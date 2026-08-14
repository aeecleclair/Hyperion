"""Unit tests for app/modules/raid/schemas_raid.py.

Focus on the Pydantic validators that encode new business rules:
- Legacy lowercase `otherschool` coercion on `situation`.
- `situation=otherSchool` requires `other_school` to be set.
- Switching back to `centrale` clears `other_school`.
- Pydantic-level required fields on the edition / volunteer schemas.
"""

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.raid import schemas_raid
from app.modules.raid.raid_type import (
    Difficulty,
    MeetingPlace,
    RaidRegistrationStatus,
    Situation,
    Size,
)

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
        captain=schemas_raid.RaidParticipantPreview(
            user_id="u1",
            edition_id=uuid4(),
            status=RaidRegistrationStatus.draft,
            payment=False,
            t_shirt_payment=False,
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
        captain=schemas_raid.RaidParticipantPreview(
            user_id="u1",
            edition_id=uuid4(),
            status=RaidRegistrationStatus.draft,
            payment=False,
            t_shirt_payment=False,
            user=_dummy_core_user("u1"),
        ),
        second=None,
        difficulty=Difficulty.sports,
        meeting_place=MeetingPlace.centrale,
    )
    assert preview.validation_progress == 10  # (2/2)*10 + 0 captain/second


# Shared helper --------------------------------------------------------------


def _dummy_core_user(uid: str):
    from app.core.groups.groups_type import AccountType
    from app.core.users.schemas_users import CoreUser

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
