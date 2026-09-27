"""Unit tests for app/modules/raid/schemas_raid.py.

Focus on the Pydantic validators that encode new business rules:
- Legacy lowercase `otherschool` coercion on `situation`.
- `situation=otherSchool` requires `other_school` to be set.
- Switching back to `centrale` clears `other_school`.
- Pydantic-level required fields on the edition / volunteer schemas.
- Team preview document counters and teammate security-file privacy.
"""

import datetime
from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.groups.groups_type import AccountType
from app.core.users.schemas_users import CoreUser
from app.modules.raid import schemas_raid
from app.modules.raid.raid_type import (
    Difficulty,
    DocumentType,
    DocumentValidation,
    MeetingPlace,
    RaidRegistrationStatus,
    Situation,
    Size,
)
from app.modules.raid.utils.utils_raid import prepare_data

# -- RaidParticipantUpdate: situation validators ---------------------------


def test_participant_update_accepts_enum_values() -> None:
    u = schemas_raid.RaidParticipantUpdate(situation=Situation.centrale)
    assert u.situation == Situation.centrale


def test_participant_update_coerces_legacy_lowercase_otherschool() -> None:
    u = schemas_raid.RaidParticipantUpdate(
        situation="otherschool",
        other_school="ECP",
    )
    assert u.situation == Situation.otherSchool
    assert u.other_school == "ECP"


def test_participant_update_coerces_legacy_suffix_otherschool() -> None:
    u = schemas_raid.RaidParticipantUpdate(
        situation="otherschool : MyPrepa",
        other_school="MyPrepa",
    )
    assert u.situation == Situation.otherSchool


def test_participant_update_coerces_camelcase_string() -> None:
    u = schemas_raid.RaidParticipantUpdate(
        situation="otherSchool",
        other_school="Other",
    )
    assert u.situation == Situation.otherSchool


def test_participant_update_rejects_otherschool_without_school_name() -> None:
    with pytest.raises(ValidationError):
        schemas_raid.RaidParticipantUpdate(situation=Situation.otherSchool)


def test_participant_update_clears_other_school_when_centrale() -> None:
    u = schemas_raid.RaidParticipantUpdate(
        situation=Situation.centrale,
        other_school="leftover value",
    )
    assert u.other_school is None


def test_participant_update_allows_empty_body() -> None:
    # A PATCH with no fields should validate (no required fields).
    schemas_raid.RaidParticipantUpdate()


# -- RaidParticipant scholarship fields -----------------------------------


def test_participant_create_scholarship_defaults_false() -> None:
    u = schemas_raid.RaidParticipantCreate(
        user_id="u1",
        edition_id=uuid4(),
        status=RaidRegistrationStatus.draft,
    )
    assert u.has_scholarship is False
    assert u.school_authorization_id is None


def test_participant_create_accepts_scholarship_fields() -> None:
    doc_id = str(uuid4())
    u = schemas_raid.RaidParticipantCreate(
        user_id="u1",
        edition_id=uuid4(),
        status=RaidRegistrationStatus.draft,
        has_scholarship=True,
        school_authorization_id=doc_id,
    )
    assert u.has_scholarship is True
    assert u.school_authorization_id == doc_id


def test_participant_update_accepts_school_authorization_id() -> None:
    doc_id = str(uuid4())
    u = schemas_raid.RaidParticipantUpdate(school_authorization_id=doc_id)
    assert u.school_authorization_id == doc_id


def test_participant_update_accepts_has_scholarship() -> None:
    """The update schema carries the scholarship flag (admin-only upstream)."""
    u = schemas_raid.RaidParticipantUpdate(has_scholarship=True)
    assert u.has_scholarship is True

    unset = schemas_raid.RaidParticipantUpdate()
    assert unset.has_scholarship is None  # absent = don't touch


def test_participant_restricted_requires_scholarship_flag() -> None:
    """The read schema exposes has_scholarship as a required field."""
    fields = schemas_raid.RaidParticipantRestricted.model_fields
    assert "has_scholarship" in fields
    assert "school_authorization_id" in fields
    assert fields["has_scholarship"].is_required()


def test_participant_update_preserves_other_school_when_other() -> None:
    u = schemas_raid.RaidParticipantUpdate(
        situation=Situation.other,
        other_school="kept",
    )
    assert u.other_school == "kept"


# -- RaidEdition(Base|Edit) --------------------------------------------------


def test_edition_base_defaults() -> None:
    e = schemas_raid.RaidEditionBase(name="Raid 2026", year=2026)
    assert e.active is False
    assert e.inscription_enabled is False
    assert e.start_date is None


def test_edition_base_requires_name_and_year() -> None:
    with pytest.raises(ValidationError):
        schemas_raid.RaidEditionBase(year=2026)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        schemas_raid.RaidEditionBase(name="x")  # type: ignore[call-arg]


def test_edition_edit_allows_partial_update() -> None:
    e = schemas_raid.RaidEditionEdit(active=True)
    assert e.active is True
    assert e.name is None


def test_edition_full_from_attributes() -> None:
    # Construct an edition with a UUID id — mirrors the ORM shape the API
    # returns to the frontend.
    eid = uuid4()
    e = schemas_raid.RaidEdition(
        id=eid,
        name="Raid",
        year=2026,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 3),
        registering_end_date=date(2026, 4, 20),
        active=True,
        inscription_enabled=True,
    )
    assert e.id == eid
    assert e.active is True


# -- RaidVolunteerBase / Edit ----------------------------------------------


def test_volunteer_base_accepts_empty() -> None:
    schemas_raid.RaidVolunteerBase()


def test_volunteer_base_accepts_full() -> None:
    v = schemas_raid.RaidVolunteerBase(
        t_shirt_size=Size.M,
        diet="veggie",
        allergy=None,
        emergency_person_name="Jane",
        emergency_person_phone="06",
    )
    assert v.t_shirt_size == Size.M


def test_volunteer_edit_is_full_partial() -> None:
    v = schemas_raid.RaidVolunteerEdit(diet="noodles")
    assert v.diet == "noodles"
    assert v.t_shirt_size is None


# -- RaidTeamPreview + RaidTeam computed validation_progress --------------


def test_team_preview_progress_with_no_participants() -> None:
    # Using enum values for difficulty/meeting_place to ensure validator passes.
    preview = schemas_raid.RaidTeamPreview(
        id="tid",
        edition_id=uuid4(),
        name="T",
        number=None,
        captain_id="u1",
        captain=schemas_raid.RaidParticipantRestricted(
            user_id="u1",
            edition_id=uuid4(),
            status=RaidRegistrationStatus.draft,
            payment=False,
            t_shirt_payment=False,
            attestation_on_honour=False,
            is_minor=False,
            has_scholarship=False,
            user=_dummy_core_user("u1"),
        ),
        second=None,
        difficulty=None,
        meeting_place=None,
    )
    # Preview has neither difficulty nor meeting place, and the preview
    # captain isn't full RaidParticipant → contributes 0 progress.
    assert preview.validation_progress == 0


def test_team_preview_progress_with_filled_meta_only() -> None:
    preview = schemas_raid.RaidTeamPreview(
        id="tid",
        edition_id=uuid4(),
        name="T",
        number=42,
        captain_id="u1",
        captain=schemas_raid.RaidParticipantRestricted(
            user_id="u1",
            edition_id=uuid4(),
            status=RaidRegistrationStatus.draft,
            payment=False,
            t_shirt_payment=False,
            attestation_on_honour=False,
            is_minor=False,
            has_scholarship=False,
            user=_dummy_core_user("u1"),
        ),
        second=None,
        difficulty=Difficulty.sports,
        meeting_place=MeetingPlace.centrale,
    )
    assert preview.validation_progress == 10  # (2/2)*10 + 0 captain/second


# Team preview document counters -------------------------------------------


def _participant_restricted(
    uid: str,
    **overrides,
) -> schemas_raid.RaidParticipantRestricted:
    fields = {
        "user_id": uid,
        "edition_id": uuid4(),
        "status": RaidRegistrationStatus.draft,
        "payment": False,
        "t_shirt_payment": False,
        "attestation_on_honour": False,
        "is_minor": False,
        "has_scholarship": False,
        "user": _dummy_core_user(uid),
    }
    fields.update(overrides)
    return schemas_raid.RaidParticipantRestricted(**fields)


def _document(validation: DocumentValidation) -> schemas_raid.Document:
    return schemas_raid.Document(
        id=str(uuid4()),
        type=DocumentType.idCard,
        name="doc",
        uploaded_at=datetime.datetime.now(tz=datetime.UTC).date(),
        validation=validation,
    )


def test_preview_document_counters_all_accepted() -> None:
    """A centrale student with every required upload accepted: 5/5."""
    doc = _document(DocumentValidation.accepted)
    participant = _participant_restricted(
        "u1",
        situation=Situation.centrale,
        id_card=doc,
        id_card_id=doc.id,
        medical_certificate=doc,
        medical_certificate_id=doc.id,
        raid_rules=doc,
        raid_rules_id=doc.id,
        student_card=doc,
        student_card_id=doc.id,
    )
    preview = schemas_raid.RaidTeamPreview(
        id="tid",
        edition_id=uuid4(),
        name="T",
        number=None,
        captain_id="u1",
        captain=participant,
        second=None,
        difficulty=None,
        meeting_place=None,
    )
    assert preview.captain.number_of_document == 4
    assert preview.captain.number_of_validated_document == 4


def test_preview_document_counters_pending_not_counted() -> None:
    """Uploaded but pending documents count in the total, not in validated."""
    accepted = _document(DocumentValidation.accepted)
    pending = _document(DocumentValidation.pending)
    participant = _participant_restricted(
        "u1",
        situation=Situation.centrale,
        id_card=accepted,
        id_card_id=accepted.id,
        medical_certificate=pending,
        medical_certificate_id=pending.id,
        raid_rules=accepted,
        raid_rules_id=accepted.id,
        student_card=accepted,
        student_card_id=accepted.id,
    )
    preview = schemas_raid.RaidTeamPreview(
        id="tid",
        edition_id=uuid4(),
        name="T",
        number=None,
        captain_id="u1",
        captain=participant,
        second=None,
        difficulty=None,
        meeting_place=None,
    )
    assert preview.captain.number_of_document == 4
    assert preview.captain.number_of_validated_document == 3


def test_preview_document_counters_scholarship_adds_required_slot() -> None:
    """has_scholarship adds the school authorization to the required total."""
    doc = _document(DocumentValidation.accepted)
    base = {
        "situation": Situation.centrale,
        "id_card": doc,
        "id_card_id": doc.id,
        "medical_certificate": doc,
        "medical_certificate_id": doc.id,
        "raid_rules": doc,
        "raid_rules_id": doc.id,
        "student_card": doc,
        "student_card_id": doc.id,
    }
    without = _participant_restricted("u1", **base)
    with_scholarship = _participant_restricted(
        "u1",
        has_scholarship=True,
        school_authorization=doc,
        school_authorization_id=doc.id,
        **base,
    )
    assert without.number_of_document == 4
    assert with_scholarship.number_of_document == 5
    assert with_scholarship.number_of_validated_document == 5


# Security-file privacy (prepare_data) --------------------------------------


def _participant_with_security_file(
    uid: str,
) -> schemas_raid.RaidParticipant:
    return schemas_raid.RaidParticipant(
        user_id=uid,
        edition_id=uuid4(),
        status=RaidRegistrationStatus.validated,
        payment=True,
        t_shirt_payment=False,
        attestation_on_honour=True,
        is_minor=False,
        has_scholarship=False,
        user=_dummy_core_user(uid),
        security_file=schemas_raid.SecurityFile(
            id="sf1",
            validation=DocumentValidation.accepted,
            asthma=False,
            consent_given=True,
            emergency_person_firstname="Jane",
            emergency_person_name="Doe",
            emergency_person_phone="+33612345678",
        ),
    )


def test_prepare_data_keeps_own_security_file() -> None:
    """The requesting user always sees their own security file."""
    participant = _participant_with_security_file("u1")
    data = prepare_data("u1", participant)
    assert data.security_file is not None
    assert data.security_file.emergency_person_phone == "+33612345678"


def test_prepare_data_hides_teammate_security_file() -> None:
    """A teammate's security file is stripped (health-data privacy)."""
    participant = _participant_with_security_file("u2")
    data = prepare_data("u1", participant)
    assert data.security_file is None


# Shared helper --------------------------------------------------------------


def _dummy_core_user(uid: str):
    return CoreUser(
        id=uid,
        email=f"{uid}@example.com",
        account_type=AccountType.student,
        school_id=uuid4(),
        name="Doe",
        firstname="John",
        nickname=None,
        birthday=None,
        promo=None,
        floor=None,
        phone=None,
        created_on=None,
    )
