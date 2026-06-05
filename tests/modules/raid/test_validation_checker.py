"""Unit tests for app/modules/raid/utils/validation_checker.py.

These tests exercise the fine-grained sub-checks that gate a participant or a
volunteer moving to `validated`, plus the pure progress/count helpers used by
the API's computed fields. The sub-checks raise HTTPException(400) with a
distinct `detail` string per failure so the frontend can i18n cleanly; we
assert the exact strings so they stay stable.
"""

# ruff: noqa: SLF001  # tests deliberately exercise private sub-checks

from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.raid import models_raid
from app.modules.raid.raid_type import (
    Difficulty,
    DocumentValidation,
    MeetingPlace,
    Situation,
    Size,
)
from app.modules.raid.utils import validation_checker


def _make_doc(validation: DocumentValidation) -> Mock:
    return Mock(spec=models_raid.Document, validation=validation)


def _make_security_file(with_contacts: bool = True) -> Mock:
    if with_contacts:
        return Mock(
            spec=models_raid.SecurityFile,
            emergency_person_firstname="Jane",
            emergency_person_name="Doe",
            emergency_person_phone="0600000000",
        )
    return Mock(
        spec=models_raid.SecurityFile,
        emergency_person_firstname=None,
        emergency_person_name=None,
        emergency_person_phone=None,
    )


def _make_validated_participant(
    *,
    edition_id=None,
    situation: Situation = Situation.centrale,
    is_minor: bool = False,
    with_student_card: bool | None = None,
    with_parent_auth: bool | None = None,
    payment: bool = True,
    t_shirt_size: Size | None = None,
    t_shirt_payment: bool = True,
    attestation: bool = True,
    with_security_file: bool = True,
    security_contacts: bool = True,
) -> Mock:
    """Assemble a participant that would pass every check by default."""
    edition_id = edition_id or uuid4()
    if with_student_card is None:
        with_student_card = situation in (Situation.centrale, Situation.otherSchool)
    if with_parent_auth is None:
        with_parent_auth = is_minor

    participant = Mock(spec=models_raid.RaidParticipant)
    participant.user_id = "user-id"
    participant.edition_id = edition_id
    participant.situation = situation
    participant.is_minor = is_minor
    participant.attestation_on_honour = attestation
    participant.payment = payment
    participant.t_shirt_size = t_shirt_size
    participant.t_shirt_payment = t_shirt_payment
    participant.id_card = _make_doc(DocumentValidation.accepted)
    participant.medical_certificate = _make_doc(DocumentValidation.accepted)
    participant.raid_rules = _make_doc(DocumentValidation.accepted)
    participant.student_card = (
        _make_doc(DocumentValidation.accepted) if with_student_card else None
    )
    participant.parent_authorization = (
        _make_doc(DocumentValidation.accepted) if with_parent_auth else None
    )
    participant.security_file = (
        _make_security_file(security_contacts) if with_security_file else None
    )
    participant.security_file_id = (
        "some-security-file-id" if with_security_file else None
    )
    participant.address = "123 rue"
    participant.bike_size = Size.M
    participant.user = Mock(phone="0600000000")
    return participant


# -- _check_edition_scope ---------------------------------------------------


def test_check_edition_scope_rejects_wrong_edition() -> None:
    p = _make_validated_participant()
    with pytest.raises(HTTPException) as exc_info:
        validation_checker._check_edition_scope(p, uuid4())
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Participant does not belong to the current edition"
    )


def test_check_edition_scope_accepts_matching_edition() -> None:
    eid = uuid4()
    p = _make_validated_participant(edition_id=eid)
    validation_checker._check_edition_scope(p, eid)  # no raise


# -- _check_attestation_signed ----------------------------------------------


def test_check_attestation_signed_rejects_when_unsigned() -> None:
    p = _make_validated_participant(attestation=False)
    with pytest.raises(HTTPException) as exc_info:
        validation_checker._check_attestation_signed(p)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Participant has not signed the attestation on honour"
    )


def test_check_attestation_signed_accepts_when_signed() -> None:
    p = _make_validated_participant(attestation=True)
    validation_checker._check_attestation_signed(p)


# -- _check_payment_done ---------------------------------------------------


def test_check_payment_done_rejects_when_unpaid() -> None:
    p = _make_validated_participant(payment=False)
    with pytest.raises(HTTPException) as exc_info:
        validation_checker._check_payment_done(p)
    assert exc_info.value.detail == "Participant payment is not done"


def test_check_payment_done_rejects_when_tshirt_unpaid() -> None:
    p = _make_validated_participant(t_shirt_size=Size.M, t_shirt_payment=False)
    with pytest.raises(HTTPException) as exc_info:
        validation_checker._check_payment_done(p)
    assert exc_info.value.detail == "Participant t-shirt payment is not done"


def test_check_payment_done_ignores_none_size() -> None:
    p = _make_validated_participant(t_shirt_size=Size.None_, t_shirt_payment=False)
    validation_checker._check_payment_done(p)  # should not raise


def test_check_payment_done_ignores_null_tshirt_size() -> None:
    p = _make_validated_participant(t_shirt_size=None, t_shirt_payment=False)
    validation_checker._check_payment_done(p)


# -- _check_security_file_complete -----------------------------------------


def test_check_security_file_missing() -> None:
    p = _make_validated_participant(with_security_file=False)
    with pytest.raises(HTTPException) as exc_info:
        validation_checker._check_security_file_complete(p)
    assert exc_info.value.detail == "Participant has no security file"


def test_check_security_file_missing_emergency_contact() -> None:
    p = _make_validated_participant(
        with_security_file=True,
        security_contacts=False,
    )
    with pytest.raises(HTTPException) as exc_info:
        validation_checker._check_security_file_complete(p)
    assert exc_info.value.detail == (
        "Participant security file is missing emergency contact"
    )


def test_check_security_file_complete_passes() -> None:
    p = _make_validated_participant()
    validation_checker._check_security_file_complete(p)


# -- _check_all_documents_accepted ----------------------------------------


def test_check_all_documents_accepted_passes_for_centrale() -> None:
    p = _make_validated_participant(situation=Situation.centrale)
    validation_checker._check_all_documents_accepted(p)


def test_check_all_documents_accepted_passes_for_other() -> None:
    p = _make_validated_participant(
        situation=Situation.other,
        with_student_card=False,
    )
    validation_checker._check_all_documents_accepted(p)


def test_check_all_documents_accepted_requires_student_card_for_otherschool() -> None:
    p = _make_validated_participant(
        situation=Situation.otherSchool,
        with_student_card=False,
    )
    with pytest.raises(HTTPException) as exc_info:
        validation_checker._check_all_documents_accepted(p)
    assert exc_info.value.detail == "Missing student card"


def test_check_all_documents_accepted_requires_parent_auth_when_minor() -> None:
    p = _make_validated_participant(
        situation=Situation.centrale,
        is_minor=True,
        with_parent_auth=False,
    )
    with pytest.raises(HTTPException) as exc_info:
        validation_checker._check_all_documents_accepted(p)
    assert exc_info.value.detail == "Missing parent authorization"


def test_check_all_documents_accepted_rejects_pending_doc() -> None:
    p = _make_validated_participant()
    p.id_card = _make_doc(DocumentValidation.pending)
    with pytest.raises(HTTPException) as exc_info:
        validation_checker._check_all_documents_accepted(p)
    assert exc_info.value.detail == "Document id card is not accepted"


def test_check_all_documents_accepted_rejects_missing_id_card() -> None:
    p = _make_validated_participant()
    p.id_card = None
    with pytest.raises(HTTPException) as exc_info:
        validation_checker._check_all_documents_accepted(p)
    assert exc_info.value.detail == "Missing id card"


# -- check_participant_validation_consistency (full orchestrator) --------


@pytest.mark.asyncio
async def test_full_participant_checker_passes_for_valid_data() -> None:
    from unittest.mock import AsyncMock

    edition_id = uuid4()
    p = _make_validated_participant(edition_id=edition_id)
    team = Mock(
        spec=models_raid.RaidTeam,
        second=Mock(),
        difficulty=Difficulty.sports,
        meeting_place=MeetingPlace.centrale,
    )

    from app.modules.raid import cruds_raid

    original = cruds_raid.get_team_by_participant_id
    cruds_raid.get_team_by_participant_id = AsyncMock(return_value=team)  # type: ignore[assignment]
    try:
        await validation_checker.check_participant_validation_consistency(
            p,
            edition_id,
            AsyncMock(),
        )
    finally:
        cruds_raid.get_team_by_participant_id = original


@pytest.mark.asyncio
async def test_full_participant_checker_fails_when_team_incomplete() -> None:
    from unittest.mock import AsyncMock

    edition_id = uuid4()
    p = _make_validated_participant(edition_id=edition_id)
    team_no_second = Mock(
        spec=models_raid.RaidTeam,
        second=None,
        difficulty=Difficulty.sports,
        meeting_place=MeetingPlace.centrale,
    )

    from app.modules.raid import cruds_raid

    original = cruds_raid.get_team_by_participant_id
    cruds_raid.get_team_by_participant_id = AsyncMock(return_value=team_no_second)  # type: ignore[assignment]
    try:
        with pytest.raises(HTTPException) as exc_info:
            await validation_checker.check_participant_validation_consistency(
                p,
                edition_id,
                AsyncMock(),
            )
        assert exc_info.value.detail == "Team is missing a second member"
    finally:
        cruds_raid.get_team_by_participant_id = original


@pytest.mark.asyncio
async def test_full_participant_checker_fails_when_no_team() -> None:
    from unittest.mock import AsyncMock

    edition_id = uuid4()
    p = _make_validated_participant(edition_id=edition_id)

    from app.modules.raid import cruds_raid

    original = cruds_raid.get_team_by_participant_id
    cruds_raid.get_team_by_participant_id = AsyncMock(return_value=None)  # type: ignore[assignment]
    try:
        with pytest.raises(HTTPException) as exc_info:
            await validation_checker.check_participant_validation_consistency(
                p,
                edition_id,
                AsyncMock(),
            )
        assert exc_info.value.detail == "Participant is not in a team"
    finally:
        cruds_raid.get_team_by_participant_id = original


# -- Volunteer checker ------------------------------------------------------


@pytest.mark.asyncio
async def test_check_volunteer_rejects_wrong_edition() -> None:
    from unittest.mock import AsyncMock

    v = Mock(
        spec=models_raid.RaidVolunteer,
        edition_id=uuid4(),
        user=Mock(phone="06"),
        emergency_person_name="N",
        emergency_person_phone="06",
    )
    with pytest.raises(HTTPException) as exc_info:
        await validation_checker.check_volunteer_validation_consistency(
            v,
            uuid4(),
            AsyncMock(),
        )
    assert exc_info.value.detail == ("Volunteer does not belong to the current edition")


@pytest.mark.asyncio
async def test_check_volunteer_rejects_missing_phone() -> None:
    from unittest.mock import AsyncMock

    eid = uuid4()
    v = Mock(
        spec=models_raid.RaidVolunteer,
        edition_id=eid,
        user=Mock(phone=None),
        emergency_person_name="N",
        emergency_person_phone="06",
    )
    with pytest.raises(HTTPException) as exc_info:
        await validation_checker.check_volunteer_validation_consistency(
            v,
            eid,
            AsyncMock(),
        )
    assert exc_info.value.detail == ("Volunteer phone is not set on the user profile")


@pytest.mark.asyncio
async def test_check_volunteer_rejects_missing_emergency_contact() -> None:
    from unittest.mock import AsyncMock

    eid = uuid4()
    v = Mock(
        spec=models_raid.RaidVolunteer,
        edition_id=eid,
        user=Mock(phone="06"),
        emergency_person_name=None,
        emergency_person_phone="06",
    )
    with pytest.raises(HTTPException) as exc_info:
        await validation_checker.check_volunteer_validation_consistency(
            v,
            eid,
            AsyncMock(),
        )
    assert exc_info.value.detail == "Volunteer emergency contact is incomplete"


@pytest.mark.asyncio
async def test_check_volunteer_passes_for_complete_profile() -> None:
    from unittest.mock import AsyncMock

    eid = uuid4()
    v = Mock(
        spec=models_raid.RaidVolunteer,
        edition_id=eid,
        user=Mock(phone="06"),
        emergency_person_name="Jane",
        emergency_person_phone="06",
        has_car=False,
        car_seats=None,
    )
    await validation_checker.check_volunteer_validation_consistency(
        v,
        eid,
        AsyncMock(),
    )


# -- Pure helpers: progress + counts ---------------------------------------


def test_compute_participant_progress_zero_for_empty_profile() -> None:
    p = Mock(
        spec=models_raid.RaidParticipant,
        address=None,
        bike_size=None,
        t_shirt_size=None,
        situation=None,
        attestation_on_honour=None,
        is_minor=False,
        id_card=None,
        medical_certificate=None,
        security_file=None,
        raid_rules=None,
        student_card=None,
        parent_authorization=None,
    )
    assert validation_checker.compute_participant_progress(p) == 0.0


def test_compute_participant_progress_high_for_complete_profile() -> None:
    p = _make_validated_participant(situation=Situation.centrale)
    # All documents accepted + most flags set -> well above partial.
    progress = validation_checker.compute_participant_progress(p)
    assert progress >= 70


def test_compute_participant_progress_partial_gives_fraction() -> None:
    p = Mock(
        spec=models_raid.RaidParticipant,
        address="x",
        bike_size=Size.M,
        t_shirt_size=None,
        situation=None,
        attestation_on_honour=None,
        is_minor=False,
        id_card=_make_doc(DocumentValidation.accepted),
        medical_certificate=None,
        security_file=None,
        raid_rules=None,
        student_card=None,
        parent_authorization=None,
    )
    progress = validation_checker.compute_participant_progress(p)
    assert 0 < progress < 100


def test_count_total_required_documents_centrale() -> None:
    p = Mock(
        spec=models_raid.RaidParticipant,
        situation=Situation.centrale,
        is_minor=False,
    )
    assert validation_checker.count_total_required_documents(p) == 4


def test_count_total_required_documents_other_minor() -> None:
    p = Mock(spec=models_raid.RaidParticipant, situation=Situation.other, is_minor=True)
    assert validation_checker.count_total_required_documents(p) == 4


def test_count_total_required_documents_centrale_minor() -> None:
    p = Mock(
        spec=models_raid.RaidParticipant,
        situation=Situation.centrale,
        is_minor=True,
    )
    assert validation_checker.count_total_required_documents(p) == 5


def test_count_accepted_documents_all_present() -> None:
    p = _make_validated_participant(situation=Situation.centrale, is_minor=True)
    # id_card + medical_certificate + raid_rules + student_card + parent_authorization
    assert validation_checker.count_accepted_documents(p) == 5


def test_count_accepted_documents_pending_not_counted() -> None:
    p = _make_validated_participant()
    p.id_card = _make_doc(DocumentValidation.pending)
    # lost id_card -> 2 (medical + raid_rules) + student_card
    assert validation_checker.count_accepted_documents(p) == 3
