"""Central validation checker for raid participants and volunteers.

The admin cannot flip a participant to `validated` until every sub-check
passes; the same applies to volunteers (with a lighter gate). Each check
raises a distinct HTTPException so the frontend can i18n cleanly.
"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.raid import cruds_raid, models_raid
from app.modules.raid.raid_type import (
    DocumentValidation,
    RaidRegistrationStatus,
    Situation,
    Size,
)


async def check_participant_validation_consistency(
    participant: models_raid.RaidParticipant,
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
    participant: models_raid.RaidParticipant,
    edition_id,
) -> None:
    if participant.edition_id != edition_id:
        raise HTTPException(
            status_code=400,
            detail="Participant does not belong to the current edition",
        )


def _check_attestation_signed(participant: models_raid.RaidParticipant) -> None:
    if not participant.attestation_on_honour:
        raise HTTPException(
            status_code=400,
            detail="Participant has not signed the attestation on honour",
        )


def _check_payment_done(participant: models_raid.RaidParticipant) -> None:
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


def _check_security_file_complete(participant: models_raid.RaidParticipant) -> None:
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


def _check_all_documents_accepted(participant: models_raid.RaidParticipant) -> None:
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
    document: models_raid.Document | None,
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
    participant: models_raid.RaidParticipant,
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
    if team.second_id is None:
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
    volunteer: models_raid.RaidVolunteer,
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


def compute_participant_progress(
    participant: models_raid.RaidParticipant,
) -> float:
    """Pure port of the former RaidParticipant.validation_progress @property.

    Kept as a read-only helper so the frontend can display a percentage while
    RaidRegistrationStatus remains the actual source of truth.
    """
    number_total = 10
    conditions = [
        participant.address,
        participant.bike_size,
        participant.t_shirt_size,
        participant.situation,
        participant.attestation_on_honour,
    ]
    number_validated: float = sum(condition is not None for condition in conditions)
    if participant.situation in (Situation.centrale, Situation.otherSchool):
        number_total += 1
        if (
            participant.student_card
            and participant.student_card.validation == DocumentValidation.accepted
        ):
            number_validated += 1
    if participant.is_minor:
        number_total += 1
        if participant.parent_authorization:
            if participant.parent_authorization.validation == DocumentValidation.accepted:
                number_validated += 1
            elif (
                participant.parent_authorization.validation
                == DocumentValidation.temporary
            ):
                number_validated += 0.5
    if (
        participant.id_card
        and participant.id_card.validation == DocumentValidation.accepted
    ):
        number_validated += 1
    if participant.medical_certificate:
        if participant.medical_certificate.validation == DocumentValidation.accepted:
            number_validated += 1
        elif (
            participant.medical_certificate.validation == DocumentValidation.temporary
        ):
            number_validated += 0.5
    if participant.security_file:
        security_validation = participant.security_file.validation
        if security_validation == DocumentValidation.accepted:
            number_validated += 1
        elif security_validation == DocumentValidation.temporary:
            number_validated += 0.5
    if (
        participant.raid_rules
        and participant.raid_rules.validation == DocumentValidation.accepted
    ):
        number_validated += 1
    return (number_validated / number_total) * 100


def compute_team_progress(team: models_raid.RaidTeam) -> float:
    """Pure port of the former RaidTeam.validation_progress @property."""
    number_validated = 0
    number_total = 2
    if team.difficulty:
        number_validated += 1
    if team.meeting_place:
        number_validated += 1
    return (number_validated / number_total) * 10 + (
        compute_participant_progress(team.captain)
        + (compute_participant_progress(team.second) if team.second else 0)
    ) * 0.45


def count_total_required_documents(participant: models_raid.RaidParticipant) -> int:
    number_total = 3
    if participant.situation in (Situation.centrale, Situation.otherSchool):
        number_total += 1
    if participant.is_minor:
        number_total += 1
    return number_total


def count_accepted_documents(participant: models_raid.RaidParticipant) -> int:
    number_validated = 0
    if (
        participant.situation in (Situation.centrale, Situation.otherSchool)
        and participant.student_card
        and participant.student_card.validation == DocumentValidation.accepted
    ):
        number_validated += 1
    if (
        participant.id_card
        and participant.id_card.validation == DocumentValidation.accepted
    ):
        number_validated += 1
    if (
        participant.medical_certificate
        and participant.medical_certificate.validation == DocumentValidation.accepted
    ):
        number_validated += 1
    if (
        participant.raid_rules
        and participant.raid_rules.validation == DocumentValidation.accepted
    ):
        number_validated += 1
    if (
        participant.is_minor
        and participant.parent_authorization
        and participant.parent_authorization.validation == DocumentValidation.accepted
    ):
        number_validated += 1
    return number_validated


__all__ = [
    "RaidRegistrationStatus",
    "check_participant_validation_consistency",
    "check_volunteer_validation_consistency",
    "compute_participant_progress",
    "compute_team_progress",
    "count_accepted_documents",
    "count_total_required_documents",
]
