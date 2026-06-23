"""End-to-end tests for the raid module endpoints.

Covers the full participant registration flow with the new edition scoping +
state machine, team lifecycle, volunteer registration flow, admin validation
gates, and permission enforcement. Identity fields (name/firstname/email/
birthday/phone) now live on `CoreUser`; tests set them via `update_user` so
the participant/volunteer payloads stay small and mirror the real API shape.
"""

import asyncio
import datetime
import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.core.groups import models_groups
from app.core.groups.groups_type import AccountType
from app.core.users import cruds_users, models_users, schemas_users
from app.modules.raid import coredata_raid, cruds_raid, models_raid, schemas_raid
from app.modules.raid.endpoints_raid import RaidPermissions
from app.modules.raid.raid_type import (
    Difficulty,
    DocumentType,
    DocumentValidation,
    MeetingPlace,
    RaidRegistrationStatus,
    Situation,
    Size,
)
from app.types.sqlalchemy import Base
from tests.commons import (
    add_account_type_permission,
    add_coredata_to_db,
    add_object_to_db,
    create_api_access_token,
    create_groups_with_permissions,
    create_user_with_groups,
    get_TestingSessionLocal,
)

# ---------------------------------------------------------------------------
# Globals populated by the module-scoped init fixture.
# ---------------------------------------------------------------------------

admin_group: models_groups.CoreGroup

active_edition: models_raid.RaidEdition

raid_admin_user: models_users.CoreUser
user_captain: models_users.CoreUser
user_second: models_users.CoreUser
user_solo: models_users.CoreUser
user_no_profile: models_users.CoreUser
user_volunteer: models_users.CoreUser
user_no_raid: models_users.CoreUser

token_admin: str
token_captain: str
token_second: str
token_solo: str
token_no_profile: str
token_volunteer: str
token_no_raid: str

doc_accepted: models_raid.Document
doc_pending: models_raid.Document


async def _set_user_identity(user_id: str, phone: str, birthday: datetime.date) -> None:
    async with get_TestingSessionLocal()() as db:
        await cruds_users.update_user(
            db,
            user_id,
            schemas_users.CoreUserUpdateAdmin(phone=phone, birthday=birthday),
        )
        await db.commit()


async def _ensure_tables_created() -> None:
    """Work around the test harness's flaky `use_lock_for_workers` path.

    In test mode the init_db startup hook may be skipped when the current
    pytest process isn't selected as the "chosen worker" by psutil. Force
    table creation so init_objects never races with it.
    """
    session_local = get_TestingSessionLocal()
    async with session_local() as db:
        engine = db.bind
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects(client) -> None:
    await _ensure_tables_created()

    # The init_db startup hook normally seeds each module's access permission
    # against the default account types. When the fallback worker selection
    # skips init_db we also need to seed them; when it runs we must not
    # double-insert. Wrap in try/except to stay idempotent.
    for account_type in AccountType:
        try:
            await add_account_type_permission(
                RaidPermissions.access_raid,
                account_type,
            )
        except Exception:  # noqa: S110
            pass

    global admin_group, active_edition
    admin_group = await create_groups_with_permissions(
        [RaidPermissions.manage_raid],
        "raid_admin",
    )

    edition = models_raid.RaidEdition(
        id=uuid.uuid4(),
        year=2026,
        name="Raid 2026",
        start_date=datetime.date(2026, 5, 1),
        end_date=datetime.date(2026, 5, 3),
        registering_end_date=datetime.date(2026, 4, 25),
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(edition)
    active_edition = edition

    await add_coredata_to_db(
        coredata_raid.RaidPrice(
            student_price=50,
            t_shirt_price=15,
            partner_price=70,
            external_price=90,
        ),
    )
    await add_coredata_to_db(coredata_raid.RaidInformation())

    global raid_admin_user, token_admin
    raid_admin_user = await create_user_with_groups([admin_group.id])
    await _set_user_identity(
        raid_admin_user.id,
        "+33600000000",
        datetime.date(1990, 1, 1),
    )
    token_admin = create_api_access_token(raid_admin_user)

    global user_captain, token_captain
    user_captain = await create_user_with_groups([])
    await _set_user_identity(user_captain.id, "+33611111111", datetime.date(2000, 6, 1))
    token_captain = create_api_access_token(user_captain)

    global user_second, token_second
    user_second = await create_user_with_groups([])
    await _set_user_identity(user_second.id, "+33622222222", datetime.date(2001, 3, 15))
    token_second = create_api_access_token(user_second)

    global user_solo, token_solo
    user_solo = await create_user_with_groups([])
    await _set_user_identity(user_solo.id, "+33633333333", datetime.date(1999, 11, 11))
    token_solo = create_api_access_token(user_solo)

    global user_no_profile, token_no_profile
    user_no_profile = await create_user_with_groups([])
    await _set_user_identity(
        user_no_profile.id,
        "+33644444444",
        datetime.date(2002, 2, 2),
    )
    token_no_profile = create_api_access_token(user_no_profile)

    global user_volunteer, token_volunteer
    user_volunteer = await create_user_with_groups([])
    await _set_user_identity(
        user_volunteer.id,
        "+33655555555",
        datetime.date(1998, 7, 7),
    )
    token_volunteer = create_api_access_token(user_volunteer)

    global user_no_raid, token_no_raid
    user_no_raid = await create_user_with_groups([])
    # Intentionally no identity update — POST /participants must 400.
    token_no_raid = create_api_access_token(user_no_raid)

    global doc_accepted, doc_pending
    doc_accepted = models_raid.Document(
        id=str(uuid.uuid4()),
        edition_id=active_edition.id,
        name="accepted.pdf",
        uploaded_at=datetime.datetime.now(tz=datetime.UTC).date(),
        type=DocumentType.idCard,
        validation=DocumentValidation.accepted,
    )
    await add_object_to_db(doc_accepted)

    doc_pending = models_raid.Document(
        id=str(uuid.uuid4()),
        edition_id=active_edition.id,
        name="pending.pdf",
        uploaded_at=datetime.datetime.now(tz=datetime.UTC).date(),
        type=DocumentType.medicalCertificate,
        validation=DocumentValidation.pending,
    )
    await add_object_to_db(doc_pending)

    captain_participant = models_raid.RaidParticipant(
        user_id=user_captain.id,
        edition_id=active_edition.id,
        status=RaidRegistrationStatus.draft,
        address="1 rue de la Doua",
        bike_size=Size.M,
        t_shirt_size=Size.M,
        situation=Situation.centrale,
        attestation_on_honour=False,
        payment=False,
        t_shirt_payment=False,
        is_minor=False,
    )
    await add_object_to_db(captain_participant)

    second_participant = models_raid.RaidParticipant(
        user_id=user_second.id,
        edition_id=active_edition.id,
        status=RaidRegistrationStatus.draft,
        situation=Situation.centrale,
        is_minor=False,
    )
    await add_object_to_db(second_participant)

    solo_participant = models_raid.RaidParticipant(
        user_id=user_solo.id,
        edition_id=active_edition.id,
        status=RaidRegistrationStatus.draft,
        situation=Situation.other,
        is_minor=False,
    )
    await add_object_to_db(solo_participant)

    main_team = models_raid.RaidTeam(
        id=str(uuid.uuid4()),
        edition_id=active_edition.id,
        name="MainTeam",
        difficulty=Difficulty.sports,
        meeting_place=MeetingPlace.centrale,
        captain_id=user_captain.id,
        second_id=user_second.id,
    )
    await add_object_to_db(main_team)

    solo_team = models_raid.RaidTeam(
        id=str(uuid.uuid4()),
        edition_id=active_edition.id,
        name="SoloTeam",
        difficulty=None,
        meeting_place=None,
        captain_id=user_solo.id,
        second_id=None,
    )
    await add_object_to_db(solo_team)


# ---------------------------------------------------------------------------
# Edition endpoints
# ---------------------------------------------------------------------------


def test_get_active_edition(client: TestClient) -> None:
    r = client.get(
        "/raid/editions/active",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(active_edition.id)


def test_list_editions_requires_admin(client: TestClient) -> None:
    r = client.get(
        "/raid/editions",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 403


def test_list_editions_as_admin(client: TestClient) -> None:
    r = client.get(
        "/raid/editions",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200
    assert any(e["id"] == str(active_edition.id) for e in r.json())


def test_create_and_delete_archive_edition(client: TestClient) -> None:
    r = client.post(
        "/raid/editions",
        json={
            "name": "Test Archive Edition",
            "year": 2020,
            "active": False,
            "inscription_enabled": False,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 201
    new_id = r.json()["id"]

    d = client.delete(
        f"/raid/editions/{new_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert d.status_code == 204


def test_delete_edition_with_participants_rejected(client: TestClient) -> None:
    r = client.delete(
        f"/raid/editions/{active_edition.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Participants: state machine
# ---------------------------------------------------------------------------


def test_get_participant_self(client: TestClient) -> None:
    r = client.get(
        f"/raid/participants/{user_captain.id}",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == user_captain.id
    assert body["status"] == "draft"
    # CoreUser is embedded on the full read schema.
    assert body["user"]["name"] == user_captain.name


def test_get_participant_other_forbidden(client: TestClient) -> None:
    r = client.get(
        f"/raid/participants/{user_captain.id}",
        headers={"Authorization": f"Bearer {token_solo}"},
    )
    assert r.status_code == 403


def test_get_participant_as_admin(client: TestClient) -> None:
    r = client.get(
        f"/raid/participants/{user_captain.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200


def test_create_participant_missing_identity_400(client: TestClient) -> None:
    r = client.post(
        "/raid/participants",
        headers={"Authorization": f"Bearer {token_no_raid}"},
    )
    assert r.status_code == 400
    assert "birthday or phone" in r.json()["detail"]


def test_create_participant_success(client: TestClient) -> None:
    r = client.post(
        "/raid/participants",
        headers={"Authorization": f"Bearer {token_no_profile}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user_id"] == user_no_profile.id
    assert body["status"] == "draft"
    assert body["edition_id"] == str(active_edition.id)


def test_create_participant_twice_rejected(client: TestClient) -> None:
    r = client.post(
        "/raid/participants",
        headers={"Authorization": f"Bearer {token_no_profile}"},
    )
    assert r.status_code == 403


def test_update_participant_in_draft(client: TestClient) -> None:
    r = client.patch(
        f"/raid/participants/{user_captain.id}",
        json={"address": "42 rue Example", "bike_size": "L"},
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 204


def test_update_participant_other_forbidden(client: TestClient) -> None:
    r = client.patch(
        f"/raid/participants/{user_captain.id}",
        json={"address": "should fail"},
        headers={"Authorization": f"Bearer {token_solo}"},
    )
    assert r.status_code == 403


def test_update_participant_legacy_situation_string(client: TestClient) -> None:
    # Grace-period coercion of `otherschool` -> Situation.otherSchool.
    r = client.patch(
        f"/raid/participants/{user_captain.id}",
        json={"situation": "otherschool", "other_school": "ECP"},
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 204


def test_update_participant_invalid_document(client: TestClient) -> None:
    r = client.patch(
        f"/raid/participants/{user_captain.id}",
        json={"id_card_id": "does-not-exist"},
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 404


def test_submit_without_attestation_400(client: TestClient) -> None:
    r = client.post(
        f"/raid/participants/{user_captain.id}/submit",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 400
    assert "Attestation" in r.json()["detail"]


def test_submit_without_documents_400(client: TestClient) -> None:
    client.post(
        f"/raid/participant/{user_captain.id}/honour",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    r = client.post(
        f"/raid/participants/{user_captain.id}/submit",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 400


def test_admin_validate_fails_before_prerequisites(client: TestClient) -> None:
    r = client.patch(
        f"/raid/participants/{user_captain.id}/validate",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 400


async def _prepare_full_validation_state() -> None:
    """Promote captain + second to every prerequisite (except difficulty/meeting)."""
    async with get_TestingSessionLocal()() as db:
        docs = {}
        for doc_type in (
            DocumentType.idCard,
            DocumentType.medicalCertificate,
            DocumentType.raidRules,
            DocumentType.studentCard,
        ):
            doc = models_raid.Document(
                id=str(uuid.uuid4()),
                edition_id=active_edition.id,
                name=f"{doc_type.value}.pdf",
                uploaded_at=datetime.datetime.now(tz=datetime.UTC).date(),
                type=doc_type,
                validation=DocumentValidation.accepted,
            )
            db.add(doc)
            docs[doc_type] = doc
        await db.flush()

        security = models_raid.SecurityFile(
            id=str(uuid.uuid4()),
            edition_id=active_edition.id,
            allergy=None,
            asthma=False,
            intensive_care_unit=None,
            intensive_care_unit_when=None,
            ongoing_treatment=None,
            sicknesses=None,
            hospitalization=None,
            surgical_operation=None,
            trauma=None,
            family=None,
            emergency_person_firstname="Jane",
            emergency_person_name="Doe",
            emergency_person_phone="0600000000",
            file_id=None,
        )
        db.add(security)
        await db.flush()

        for uid in (user_captain.id, user_second.id):
            await db.execute(
                update(models_raid.RaidParticipant)
                .where(
                    models_raid.RaidParticipant.user_id == uid,
                    models_raid.RaidParticipant.edition_id == active_edition.id,
                )
                .values(
                    id_card_id=docs[DocumentType.idCard].id,
                    medical_certificate_id=docs[DocumentType.medicalCertificate].id,
                    raid_rules_id=docs[DocumentType.raidRules].id,
                    student_card_id=docs[DocumentType.studentCard].id,
                    security_file_id=security.id,
                    attestation_on_honour=True,
                    payment=True,
                    t_shirt_payment=True,
                    situation=Situation.centrale,
                ),
            )
        await db.commit()


def test_admin_validate_full_happy_path(client: TestClient) -> None:
    asyncio.get_event_loop().run_until_complete(_prepare_full_validation_state())

    r = client.patch(
        f"/raid/participants/{user_captain.id}/validate",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 204, r.json()

    r = client.get(
        f"/raid/participants/{user_captain.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.json()["status"] == "validated"


def test_non_admin_update_blocked_after_validation(client: TestClient) -> None:
    r = client.patch(
        f"/raid/participants/{user_captain.id}",
        json={"address": "new addr"},
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 400


def test_admin_update_still_allowed(client: TestClient) -> None:
    r = client.patch(
        f"/raid/participants/{user_captain.id}",
        json={"diet": "veggie"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 204


def test_self_reopen_validated_403(client: TestClient) -> None:
    r = client.post(
        f"/raid/participants/{user_captain.id}/reopen",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 403


def test_admin_reopen_to_draft(client: TestClient) -> None:
    r = client.post(
        f"/raid/participants/{user_captain.id}/reopen",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 204
    r2 = client.get(
        f"/raid/participants/{user_captain.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r2.json()["status"] == "draft"


def test_cancel_by_self(client: TestClient) -> None:
    r = client.patch(
        f"/raid/participants/{user_solo.id}/cancel",
        headers={"Authorization": f"Bearer {token_solo}"},
    )
    assert r.status_code == 204
    r2 = client.get(
        f"/raid/participants/{user_solo.id}",
        headers={"Authorization": f"Bearer {token_solo}"},
    )
    assert r2.json()["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


def test_list_teams_requires_admin(client: TestClient) -> None:
    r = client.get(
        "/raid/teams",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 403


def test_list_teams_as_admin(client: TestClient) -> None:
    r = client.get(
        "/raid/teams",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 2


def test_get_team_by_participant(client: TestClient) -> None:
    r = client.get(
        f"/raid/participants/{user_captain.id}/team",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 200
    assert r.json()["captain"]["user_id"] == user_captain.id


def test_update_team_by_captain(client: TestClient) -> None:
    team = client.get(
        f"/raid/participants/{user_captain.id}/team",
        headers={"Authorization": f"Bearer {token_captain}"},
    ).json()
    r = client.patch(
        f"/raid/teams/{team['id']}",
        json={"name": "MainTeam-Renamed"},
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


def test_upload_document(client: TestClient) -> None:
    r = client.post(
        "/raid/document/idCard",
        files={"file": ("idCard.pdf", b"blob", "application/pdf")},
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 201


def test_validate_document_requires_admin(client: TestClient) -> None:
    r = client.post(
        f"/raid/document/{doc_pending.id}/validate?validation=accepted",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 403


def test_validate_document_as_admin(client: TestClient) -> None:
    r = client.post(
        f"/raid/document/{doc_pending.id}/validate?validation=accepted",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------


def test_payment_url_requires_participant(client: TestClient) -> None:
    r = client.get(
        "/raid/pay",
        headers={"Authorization": f"Bearer {token_no_raid}"},
    )
    assert r.status_code == 403


def test_confirm_payment_requires_admin(client: TestClient) -> None:
    r = client.post(
        f"/raid/participant/{user_second.id}/payment",
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 403


def test_confirm_payment_as_admin(client: TestClient) -> None:
    r = client.post(
        f"/raid/participant/{user_second.id}/payment",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 204


def test_confirm_tshirt_payment_requires_size(client: TestClient) -> None:
    r = client.post(
        f"/raid/participant/{user_no_profile.id}/t_shirt_payment",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    # user_no_profile has no t_shirt_size set.
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Volunteers
# ---------------------------------------------------------------------------


def test_participant_cannot_register_as_volunteer(client: TestClient) -> None:
    r = client.post(
        "/raid/volunteers",
        json={},
        headers={"Authorization": f"Bearer {token_captain}"},
    )
    assert r.status_code == 400


def test_create_volunteer(client: TestClient) -> None:
    r = client.post(
        "/raid/volunteers",
        json={
            "diet": "veggie",
            "emergency_person_name": "Jane Doe",
            "emergency_person_phone": "+33611111111",
            "has_car": True,
            "car_seats": 4,
            "is_parcours_helper": True,
        },
        headers={"Authorization": f"Bearer {token_volunteer}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["validated"] is False
    assert body["cancelled"] is False
    assert body["has_car"] is True
    assert body["car_seats"] == 4
    assert body["is_parcours_helper"] is True


def test_create_volunteer_twice_rejected(client: TestClient) -> None:
    r = client.post(
        "/raid/volunteers",
        json={},
        headers={"Authorization": f"Bearer {token_volunteer}"},
    )
    assert r.status_code == 403


def test_volunteer_cannot_become_participant(client: TestClient) -> None:
    r = client.post(
        "/raid/participants",
        headers={"Authorization": f"Bearer {token_volunteer}"},
    )
    assert r.status_code == 400


def test_get_my_volunteer(client: TestClient) -> None:
    r = client.get(
        "/raid/volunteers/me",
        headers={"Authorization": f"Bearer {token_volunteer}"},
    )
    assert r.status_code == 200
    assert r.json()["user_id"] == user_volunteer.id


def test_list_volunteers_admin_only(client: TestClient) -> None:
    r = client.get(
        "/raid/volunteers",
        headers={"Authorization": f"Bearer {token_volunteer}"},
    )
    assert r.status_code == 403


def test_list_volunteers_as_admin(client: TestClient) -> None:
    r = client.get(
        "/raid/volunteers",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200
    assert any(v["user_id"] == user_volunteer.id for v in r.json())


def test_update_volunteer_self(client: TestClient) -> None:
    r = client.patch(
        f"/raid/volunteers/{user_volunteer.id}",
        json={"diet": "noodles only"},
        headers={"Authorization": f"Bearer {token_volunteer}"},
    )
    assert r.status_code == 204


def test_validate_volunteer_fails_with_car_but_no_seats(
    client: TestClient,
) -> None:
    async def _break_car():
        async with get_TestingSessionLocal()() as db:
            await db.execute(
                update(models_raid.RaidVolunteer)
                .where(
                    models_raid.RaidVolunteer.user_id == user_volunteer.id,
                    models_raid.RaidVolunteer.edition_id == active_edition.id,
                )
                .values(has_car=True, car_seats=None),
            )
            await db.commit()

    asyncio.get_event_loop().run_until_complete(_break_car())

    r = client.patch(
        f"/raid/volunteers/{user_volunteer.id}/validate",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 400
    assert "car_seats" in r.json()["detail"]


def test_validate_volunteer_success(client: TestClient) -> None:
    async def _restore():
        async with get_TestingSessionLocal()() as db:
            await db.execute(
                update(models_raid.RaidVolunteer)
                .where(
                    models_raid.RaidVolunteer.user_id == user_volunteer.id,
                    models_raid.RaidVolunteer.edition_id == active_edition.id,
                )
                .values(has_car=True, car_seats=4),
            )
            await db.commit()

    asyncio.get_event_loop().run_until_complete(_restore())

    r = client.patch(
        f"/raid/volunteers/{user_volunteer.id}/validate",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 204


def test_delete_validated_volunteer_self_forbidden(client: TestClient) -> None:
    r = client.delete(
        f"/raid/volunteers/{user_volunteer.id}",
        headers={"Authorization": f"Bearer {token_volunteer}"},
    )
    assert r.status_code == 403


def test_delete_validated_volunteer_as_admin(client: TestClient) -> None:
    r = client.delete(
        f"/raid/volunteers/{user_volunteer.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 204


def test_get_volunteer_me_after_delete(client: TestClient) -> None:
    r = client.get(
        "/raid/volunteers/me",
        headers={"Authorization": f"Bearer {token_volunteer}"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Raw CRUD integration tests (edition-aware)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_active_edition_crud() -> None:
    async with get_TestingSessionLocal()() as db:
        edition = await cruds_raid.get_active_edition(db)
        assert edition is not None
        assert edition.id == active_edition.id


@pytest.mark.asyncio
async def test_get_all_participants_scoped_by_edition() -> None:
    async with get_TestingSessionLocal()() as db:
        all_here = await cruds_raid.get_all_participants(active_edition.id, db)
        assert len(all_here) >= 3
        drafts = await cruds_raid.get_all_participants(
            active_edition.id,
            db,
            status=RaidRegistrationStatus.draft,
        )
        assert all(p.status == RaidRegistrationStatus.draft for p in drafts)


@pytest.mark.asyncio
async def test_is_user_a_participant_true_and_false() -> None:
    async with get_TestingSessionLocal()() as db:
        assert await cruds_raid.is_user_a_participant(
            user_second.id,
            active_edition.id,
            db,
        )
        assert not await cruds_raid.is_user_a_participant(
            user_no_raid.id,
            active_edition.id,
            db,
        )


@pytest.mark.asyncio
async def test_get_team_by_participant_id_finds_both_roles() -> None:
    async with get_TestingSessionLocal()() as db:
        captain_team = await cruds_raid.get_team_by_participant_id(
            user_captain.id,
            active_edition.id,
            db,
        )
        second_team = await cruds_raid.get_team_by_participant_id(
            user_second.id,
            active_edition.id,
            db,
        )
        assert captain_team is not None
        assert second_team is not None
        assert captain_team.id == second_team.id


@pytest.mark.asyncio
async def test_get_number_of_teams_counts() -> None:
    async with get_TestingSessionLocal()() as db:
        n = await cruds_raid.get_number_of_teams(active_edition.id, db)
        assert n >= 2


@pytest.mark.asyncio
async def test_volunteer_crud_roundtrip() -> None:
    user = await create_user_with_groups([])
    await _set_user_identity(user.id, "+33600000001", datetime.date(1998, 1, 1))

    async with get_TestingSessionLocal()() as db:
        v = schemas_raid.RaidVolunteerCreate(
            user_id=user.id,
            edition_id=active_edition.id,
            created_at=datetime.datetime.now(tz=datetime.UTC),
            validated=False,
            cancelled=False,
        )
        await cruds_raid.create_volunteer(v, db)
        await db.commit()
    async with get_TestingSessionLocal()() as db:
        got = await cruds_raid.get_volunteer_by_user_id(
            user.id,
            active_edition.id,
            db,
        )
        assert got is not None
        assert got.validated is False

        all_v = await cruds_raid.get_all_volunteers_by_edition(
            active_edition.id,
            db,
        )
        assert any(x.user_id == user.id for x in all_v)

        validated = await cruds_raid.get_all_volunteers_by_edition(
            active_edition.id,
            db,
            validated=True,
        )
        assert not any(x.user_id == user.id for x in validated)

        await cruds_raid.update_volunteer_validation(
            user.id,
            active_edition.id,
            True,
            db,
        )
        await db.commit()

    async with get_TestingSessionLocal()() as db:
        re_read = await cruds_raid.get_volunteer_by_user_id(
            user.id,
            active_edition.id,
            db,
        )
        assert re_read is not None
        assert re_read.validated is True


@pytest.mark.asyncio
async def test_edition_crud_create_read_delete() -> None:
    async with get_TestingSessionLocal()() as db:
        new_edition = schemas_raid.RaidEdition(
            id=uuid.uuid4(),
            year=2019,
            name="Legacy",
            start_date=None,
            end_date=None,
            registering_end_date=None,
            active=False,
            inscription_enabled=False,
        )
        await cruds_raid.create_edition(new_edition, db)
        await db.commit()
    async with get_TestingSessionLocal()() as db:
        all_editions = await cruds_raid.get_all_editions(db)
        assert any(e.id == new_edition.id for e in all_editions)
        await cruds_raid.delete_edition(new_edition.id, db)
        await db.commit()
