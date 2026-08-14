"""Central validation checker for raid participants and volunteers.

The admin cannot flip a participant to `validated` until every sub-check
passes; the same applies to volunteers (with a lighter gate). Each check
raises a distinct HTTPException so the frontend can i18n cleanly.
"""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.raid import cruds_raid, schemas_raid
from app.modules.raid.raid_type import (
    DocumentValidation,
    RaidRegistrationStatus,
    Situation,
    Size,
)


async def check_participant_validation_consistency(
    participant: schemas_raid.RaidParticipant,
    edition_id,
    db: AsyncSession,
) -> None:
    """Run every gate required before an admin can set status=validated."""

    _check_edition_scope(participant, edition_id)
    _check_attestation_signed(participant)
    _check_payment_done(participant)
    _check_security_file_complete(participant)
    _check_all_documents_accepted(participant)
    await _check_team_complete(participant, db)


def _check_edition_scope(
    participant: schemas_raid.RaidParticipant,
    edition_id,
) -> None:
    if participant.edition_id != edition_id:
        raise HTTPException(
            status_code=400,
            detail="Participant does not belong to the current edition",
        )


def _check_attestation_signed(participant: schemas_raid.RaidParticipant) -> None:
    if not participant.attestation_on_honour:
        raise HTTPException(
            status_code=400,
            detail="Participant has not signed the attestation on honour",
        )


def _check_payment_done(participant: schemas_raid.RaidParticipant) -> None:
    if not participant.payment:
        raise HTTPException(
            status_code=400,
            detail="Participant payment is not done",
        )
    if (
        participant.t_shirt_size is not None
        and participant.t_shirt_size != Size.None_
        and not participant.t_shirt_payment
    ):
        raise HTTPException(
            status_code=400,
            detail="Participant t-shirt payment is not done",
        )


def _check_security_file_complete(participant: schemas_raid.RaidParticipant) -> None:
    security_file = participant.security_file
    if security_file is None:
        raise HTTPException(
            status_code=400,
            detail="Participant has no security file",
        )
    if not (
        security_file.emergency_person_firstname
        and security_file.emergency_person_name
        and security_file.emergency_person_phone
    ):
        raise HTTPException(
            status_code=400,
            detail="Participant security file is missing emergency contact",
        )


def _check_all_documents_accepted(participant: schemas_raid.RaidParticipant) -> None:
    _check_document_accepted(participant.id_card, "id card")
    _check_document_accepted(participant.medical_certificate, "medical certificate")
    _check_document_accepted(participant.raid_rules, "raid rules")
    if participant.situation in (Situation.centrale, Situation.otherSchool):
        _check_document_accepted(participant.student_card, "student card")
    if participant.is_minor:
        _check_document_accepted(
            participant.parent_authorization,
            "parent authorization",
        )


def _check_document_accepted(
    document: schemas_raid.Document | None,
    label: str,
) -> None:
    if document is None:
        raise HTTPException(
            status_code=400,
            detail=f"Missing {label}",
        )
    if document.validation != DocumentValidation.accepted:
        raise HTTPException(
            status_code=400,
            detail=f"Document {label} is not accepted",
        )


async def _check_team_complete(
    participant: schemas_raid.RaidParticipant,
    db: AsyncSession,
) -> None:
    team = await cruds_raid.get_team_by_participant_id(
        participant.user_id,
        participant.edition_id,
        db,
    )
    if team is None:
        raise HTTPException(
            status_code=400,
            detail="Participant is not in a team",
        )
    if team.second is None:
        raise HTTPException(
            status_code=400,
            detail="Team is missing a second member",
        )
    if team.difficulty is None:
        raise HTTPException(
            status_code=400,
            detail="Team has no chosen difficulty",
        )
    if team.meeting_place is None:
        raise HTTPException(
            status_code=400,
            detail="Team has no chosen meeting place",
        )


async def check_volunteer_validation_consistency(
    volunteer: schemas_raid.RaidVolunteer,
    edition_id,
    db: AsyncSession,
) -> None:
    if volunteer.edition_id != edition_id:
        raise HTTPException(
            status_code=400,
            detail="Volunteer does not belong to the current edition",
        )
    if not (volunteer.user and volunteer.user.phone):
        raise HTTPException(
            status_code=400,
            detail="Volunteer phone is not set on the user profile",
        )
    if not (volunteer.emergency_person_name and volunteer.emergency_person_phone):
        raise HTTPException(
            status_code=400,
            detail="Volunteer emergency contact is incomplete",
        )
    if volunteer.has_car and (
        volunteer.car_seats is None or volunteer.car_seats <= 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Volunteer has a car but car_seats is missing or invalid",
        )


# ---------------------------------------------------------------------------
# Declarative progress / required-documents rules
# ---------------------------------------------------------------------------
#
# The "registration completeness" used to be hand-rolled with nested ifs and
# magic constants (a `number_total = 10` baseline that did not actually map to
# 10 slots once you counted them). The model below makes every slot explicit
# so the rules can be read top-to-bottom.


@dataclass(frozen=True)
class _ParticipantContext:
    """Flags that decide which document slots apply to a given participant."""

    situation: Situation | None
    is_minor: bool


@dataclass(frozen=True)
class _DocumentRule:
    """One progress slot tied to a participant attribute.

    `applies(context)` decides whether this slot exists for the participant
    at all; `counts_temporary` lets a `DocumentValidation.temporary` score
    half a slot rather than zero; `is_required_document` distinguishes actual
    uploads (id card, medical certificate, …) from the SecurityFile form,
    which contributes to overall progress but is not exposed in the
    `n / total documents` counter the frontend shows.
    """

    attr: str
    applies: Callable[[_ParticipantContext], bool]
    counts_temporary: bool = False
    is_required_document: bool = True


_STUDENT_SITUATIONS = (Situation.centrale, Situation.otherSchool)

_DOCUMENT_RULES: tuple[_DocumentRule, ...] = (
    _DocumentRule("id_card", applies=lambda _c: True),
    _DocumentRule(
        "medical_certificate", applies=lambda _c: True, counts_temporary=True,
    ),
    _DocumentRule(
        "security_file",
        applies=lambda _c: True,
        counts_temporary=True,
        is_required_document=False,
    ),
    _DocumentRule("raid_rules", applies=lambda _c: True),
    _DocumentRule(
        "student_card",
        applies=lambda c: c.situation in _STUDENT_SITUATIONS,
    ),
    _DocumentRule(
        "parent_authorization",
        applies=lambda c: c.is_minor,
        counts_temporary=True,
    ),
)

# Profile fields that each count one slot when set on the participant.
_PROFILE_FIELDS: tuple[str, ...] = (
    "address",
    "bike_size",
    "t_shirt_size",
    "situation",
    "attestation_on_honour",
)


def _context(participant: schemas_raid.RaidParticipant) -> _ParticipantContext:
    return _ParticipantContext(
        situation=participant.situation,
        is_minor=participant.is_minor,
    )


def _applicable_rules(ctx: _ParticipantContext) -> list[_DocumentRule]:
    return [rule for rule in _DOCUMENT_RULES if rule.applies(ctx)]


def _score(participant: schemas_raid.RaidParticipant, rule: _DocumentRule) -> float:
    doc = getattr(participant, rule.attr)
    if doc is None:
        return 0.0
    if doc.validation == DocumentValidation.accepted:
        return 1.0
    if rule.counts_temporary and doc.validation == DocumentValidation.temporary:
        return 0.5
    return 0.0


def compute_participant_progress(
    participant: schemas_raid.RaidParticipant,
) -> float:
    """Return the participant's registration progress as a 0-100 percentage.

    Read-only helper so the frontend can show a completion bar; the actual
    source of truth for whether a participant is allowed to take part remains
    their `RaidRegistrationStatus`.
    """
    rules = _applicable_rules(_context(participant))
    total = len(_PROFILE_FIELDS) + len(rules)
    if not total:
        return 0.0
    filled_profile = sum(
        getattr(participant, field) is not None for field in _PROFILE_FIELDS
    )
    scored_docs = sum(_score(participant, rule) for rule in rules)
    return ((filled_profile + scored_docs) / total) * 100


def compute_team_progress(team: schemas_raid.RaidTeam) -> float:
    """Combine the two participants' progress with the team-level metadata."""
    team_filled = int(team.difficulty is not None) + int(team.meeting_place is not None)
    team_share = (team_filled / 2) * 10
    captain = compute_participant_progress(team.captain)
    second = compute_participant_progress(team.second) if team.second else 0
    return team_share + (captain + second) * 0.45


def count_total_required_documents(participant: schemas_raid.RaidParticipant) -> int:
    """Number of upload slots required for this participant's profile."""
    return sum(
        1
        for rule in _applicable_rules(_context(participant))
        if rule.is_required_document
    )


def count_accepted_documents(participant: schemas_raid.RaidParticipant) -> int:
    """Number of required uploads that are currently in the `accepted` state."""
    return sum(
        1
        for rule in _applicable_rules(_context(participant))
        if rule.is_required_document
        and (doc := getattr(participant, rule.attr)) is not None
        and doc.validation == DocumentValidation.accepted
    )


__all__ = [
    "RaidRegistrationStatus",
    "check_participant_validation_consistency",
    "check_volunteer_validation_consistency",
    "compute_participant_progress",
    "compute_team_progress",
    "count_accepted_documents",
    "count_total_required_documents",
]
