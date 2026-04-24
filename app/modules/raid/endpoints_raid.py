import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType
from app.core.payment.payment_tool import PaymentTool
from app.core.payment.types_payment import HelloAssoConfigName
from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import models_users, schemas_users
from app.dependencies import (
    get_db,
    get_payment_tool,
    is_user_allowed_to,
)
from app.modules.raid import coredata_raid, cruds_raid, models_raid, schemas_raid
from app.modules.raid.factory_raid import RaidFactory
from app.modules.raid.dependencies_raid import (
    ensure_user_is_not_participant_in_edition,
    ensure_user_is_not_volunteer_in_edition,
    get_current_raid_edition,
    get_participant_or_404,
    get_volunteer_or_404,
)
from app.modules.raid.raid_type import (
    DocumentType,
    DocumentValidation,
    RaidRegistrationStatus,
    Size,
)
from app.modules.raid.utils.utils_raid import (
    calculate_raid_payment,
    get_all_security_files_zip,
    get_all_team_files_zip,
    validate_payment,
    will_birthday_be_minor_on,
)
from app.modules.raid.utils.validation_checker import (
    check_participant_validation_consistency,
    check_volunteer_validation_consistency,
)
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import (
    delete_all_folder_from_data,
    get_core_data,
    get_file_from_data,
    get_random_string,
    has_user_permission,
    save_file_as_data,
    set_core_data,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


class RaidPermissions(ModulePermissions):
    access_raid = "access_raid"
    manage_raid = "manage_raid"


module = Module(
    root="raid",
    tag="Raid",
    payment_callback=validate_payment,
    default_allowed_account_types=list(AccountType),
    factory=RaidFactory(),
    permissions=RaidPermissions,
)


# ---------------------------------------------------------------------------
# Editions
# ---------------------------------------------------------------------------


@module.router.get(
    "/raid/editions",
    response_model=list[schemas_raid.RaidEdition],
    status_code=200,
)
async def list_editions(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    return await cruds_raid.get_all_editions(db)


@module.router.get(
    "/raid/editions/active",
    response_model=schemas_raid.RaidEdition,
    status_code=200,
)
async def get_active_edition(
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    return edition


@module.router.post(
    "/raid/editions",
    response_model=schemas_raid.RaidEdition,
    status_code=201,
)
async def create_edition(
    edition: schemas_raid.RaidEditionBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    if edition.active:
        await cruds_raid.deactivate_all_editions(db)
    model_edition = models_raid.RaidEdition(
        id=uuid.uuid4(),
        name=edition.name,
        year=edition.year,
        start_date=edition.start_date,
        end_date=edition.end_date,
        registering_end_date=edition.registering_end_date,
        active=edition.active,
        inscription_enabled=edition.inscription_enabled,
    )
    return await cruds_raid.create_edition(model_edition, db)


@module.router.patch(
    "/raid/editions/{edition_id}",
    status_code=204,
)
async def update_edition(
    edition_id: uuid.UUID,
    edit: schemas_raid.RaidEditionEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    existing = await cruds_raid.get_edition_by_id(edition_id, db)
    if not existing:
        raise HTTPException(status_code=404, detail="Edition not found")
    if edit.active is True and not existing.active:
        await cruds_raid.deactivate_all_editions(db)
    await cruds_raid.update_edition(edition_id, edit, db)


@module.router.delete(
    "/raid/editions/{edition_id}",
    status_code=204,
)
async def delete_edition(
    edition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    participants = await cruds_raid.get_all_participants(edition_id, db)
    if participants:
        raise HTTPException(
            status_code=400,
            detail="Edition has participants; cannot delete",
        )
    await cruds_raid.delete_edition(edition_id, db)


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------


@module.router.get(
    "/raid/participants/{user_id}",
    response_model=schemas_raid.RaidParticipant,
    status_code=200,
)
async def get_participant_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    if user_id != user.id and not await has_user_permission(
        user,
        RaidPermissions.manage_raid,
        db,
    ):
        raise HTTPException(
            status_code=403,
            detail="You can not get data of another user",
        )
    return await get_participant_or_404(user_id, edition.id, db)


@module.router.post(
    "/raid/participants",
    response_model=schemas_raid.RaidParticipant,
    status_code=201,
)
async def create_participant(
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    db: AsyncSession = Depends(get_db),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    """Create a participant. Identity (name/firstname/email/birthday/phone)
    is read from the CoreUser and must already be set there."""
    if await cruds_raid.is_user_a_participant(user.id, edition.id, db):
        raise HTTPException(status_code=403, detail="You are already a participant.")
    await ensure_user_is_not_volunteer_in_edition(user.id, edition.id, db)

    if not user.birthday or not user.phone:
        raise HTTPException(
            status_code=400,
            detail="Your user profile is missing birthday or phone; please update it first.",
        )

    raid_information = await get_core_data(coredata_raid.RaidInformation, db)
    is_minor = will_birthday_be_minor_on(
        birthday=user.birthday,
        raid_start_date=raid_information.raid_start_date,
    )

    db_participant = models_raid.RaidParticipant(
        user_id=user.id,
        edition_id=edition.id,
        status=RaidRegistrationStatus.draft,
        is_minor=is_minor,
    )
    await cruds_raid.create_participant(db_participant, db)
    return await get_participant_or_404(user.id, edition.id, db)


@module.router.patch(
    "/raid/participants/{user_id}",
    status_code=204,
)
async def update_participant(
    user_id: str,
    participant_update: schemas_raid.RaidParticipantUpdate,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    db: AsyncSession = Depends(get_db),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    saved_participant = await get_participant_or_404(user_id, edition.id, db)

    is_admin = await has_user_permission(user, RaidPermissions.manage_raid, db)
    if user.id != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="You are not the participant.")
    if not is_admin and saved_participant.status != RaidRegistrationStatus.draft:
        raise HTTPException(
            status_code=400,
            detail="Participant is not in draft state; reopen first",
        )

    if (
        saved_participant.t_shirt_payment
        and participant_update.t_shirt_size == Size.None_
    ):
        participant_update.t_shirt_size = saved_participant.t_shirt_size

    for attr, label in (
        ("id_card_id", "id_card"),
        ("medical_certificate_id", "medical_certificate"),
        ("student_card_id", "student_card"),
        ("raid_rules_id", "raid_rules"),
        ("parent_authorization_id", "parent_authorization"),
    ):
        doc_id = getattr(participant_update, attr)
        if doc_id and not await cruds_raid.get_document_by_id(doc_id, db):
            raise HTTPException(
                status_code=404,
                detail=f"Document {label} not found.",
            )

    if participant_update.security_file_id:
        if not await cruds_raid.get_security_file_by_security_id(
            participant_update.security_file_id,
            db,
        ):
            raise HTTPException(status_code=404, detail="Security_file not found.")

    values = participant_update.model_dump(exclude_none=True)
    await cruds_raid.update_participant(user_id, edition.id, values, db)


@module.router.post(
    "/raid/participants/{user_id}/submit",
    status_code=204,
)
async def submit_participant(
    user_id: str,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    db: AsyncSession = Depends(get_db),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    if user_id != user.id:
        raise HTTPException(status_code=403, detail="You are not the participant.")
    participant = await get_participant_or_404(user_id, edition.id, db)
    if participant.status != RaidRegistrationStatus.draft:
        raise HTTPException(status_code=400, detail="Participant is not a draft")
    # Light gate: attestation + security file + docs accepted + payment + team.
    # Team/payment may legitimately be not done yet at submit time, so only
    # check attestation + security file + presence of docs here.
    if not participant.attestation_on_honour:
        raise HTTPException(
            status_code=400,
            detail="Attestation on honour not signed",
        )
    if participant.security_file_id is None:
        raise HTTPException(status_code=400, detail="Security file missing")
    if not (
        participant.id_card_id
        and participant.medical_certificate_id
        and participant.raid_rules_id
    ):
        raise HTTPException(status_code=400, detail="Required documents missing")
    await cruds_raid.update_participant_status(
        user_id,
        edition.id,
        RaidRegistrationStatus.submitted,
        db,
    )


@module.router.post(
    "/raid/participants/{user_id}/reopen",
    status_code=204,
)
async def reopen_participant(
    user_id: str,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    db: AsyncSession = Depends(get_db),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    is_admin = await has_user_permission(user, RaidPermissions.manage_raid, db)
    if user_id != user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You are not the participant.")
    participant = await get_participant_or_404(user_id, edition.id, db)
    if participant.status == RaidRegistrationStatus.validated and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Cannot reopen a validated participant",
        )
    await cruds_raid.update_participant_status(
        user_id,
        edition.id,
        RaidRegistrationStatus.draft,
        db,
    )


@module.router.patch(
    "/raid/participants/{user_id}/validate",
    status_code=204,
)
async def validate_participant(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    participant = await get_participant_or_404(user_id, edition.id, db)
    await check_participant_validation_consistency(participant, edition.id, db)
    await cruds_raid.update_participant_status(
        user_id,
        edition.id,
        RaidRegistrationStatus.validated,
        db,
    )


@module.router.patch(
    "/raid/participants/{user_id}/cancel",
    status_code=204,
)
async def cancel_participant(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    is_admin = await has_user_permission(user, RaidPermissions.manage_raid, db)
    participant = await get_participant_or_404(user_id, edition.id, db)
    if user_id != user.id and not is_admin:
        raise HTTPException(status_code=403, detail="You are not the participant.")
    if participant.status == RaidRegistrationStatus.validated and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can cancel a validated participant",
        )
    await cruds_raid.update_participant_status(
        user_id,
        edition.id,
        RaidRegistrationStatus.cancelled,
        db,
    )


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


@module.router.post(
    "/raid/teams",
    response_model=schemas_raid.RaidTeam,
    status_code=201,
)
async def create_team(
    team: schemas_raid.RaidTeamBase,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    db: AsyncSession = Depends(get_db),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    if not await cruds_raid.is_user_a_participant(user.id, edition.id, db):
        raise HTTPException(status_code=403, detail="You are not a participant.")
    if await cruds_raid.get_team_by_participant_id(user.id, edition.id, db):
        raise HTTPException(status_code=403, detail="You already have a team.")

    db_team = models_raid.RaidTeam(
        id=str(uuid.uuid4()),
        edition_id=edition.id,
        name=team.name,
        number=None,
        captain_id=user.id,
        second_id=None,
        difficulty=None,
    )
    await cruds_raid.create_team(db_team, db)
    return await cruds_raid.get_team_by_id(team_id=db_team.id, db=db)


@module.router.get(
    "/raid/participants/{user_id}/team",
    response_model=schemas_raid.RaidTeam,
    status_code=200,
)
async def get_team_by_participant_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="You are not the participant.")
    participant_team = await cruds_raid.get_team_by_participant_id(
        user_id,
        edition.id,
        db,
    )
    if not participant_team:
        raise HTTPException(status_code=404, detail="You do not have a team.")
    return participant_team


@module.router.get(
    "/raid/teams",
    response_model=list[schemas_raid.RaidTeamPreview],
    status_code=200,
)
async def get_all_teams(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    return await cruds_raid.get_all_teams(edition.id, db)


@module.router.get(
    "/raid/teams/{team_id}",
    response_model=schemas_raid.RaidTeam,
    status_code=200,
)
async def get_team_by_id(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    team = await cruds_raid.get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
    return team


@module.router.patch(
    "/raid/teams/{team_id}",
    status_code=204,
)
async def update_team(
    team_id: str,
    team: schemas_raid.RaidTeamUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    existing_team = await cruds_raid.get_team_by_participant_id(user.id, edition.id, db)
    is_admin = await has_user_permission(user, RaidPermissions.manage_raid, db)
    if existing_team is None and not is_admin:
        raise HTTPException(status_code=404, detail="Team not found.")
    if existing_team is not None and existing_team.id != team_id and not is_admin:
        raise HTTPException(status_code=403, detail="You can only edit your own team.")
    await cruds_raid.update_team(team_id, team, db)


@module.router.delete(
    "/raid/teams/{team_id}",
    status_code=204,
)
async def delete_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    team = await cruds_raid.get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=400, detail="This team does not exists")
    await cruds_raid.delete_team_invite_tokens(team_id, db)
    await cruds_raid.delete_team(team_id, db)


@module.router.delete(
    "/raid/teams",
    status_code=204,
)
async def delete_all_teams(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    """Wipe all teams and participants of the active edition."""
    await cruds_raid.delete_all_invite_tokens(edition.id, db)
    await cruds_raid.delete_all_teams(edition.id, db)
    await cruds_raid.delete_all_participant(edition.id, db)
    delete_all_folder_from_data("raid")


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@module.router.post(
    "/raid/document/{document_type}",
    response_model=schemas_raid.DocumentCreation,
    status_code=201,
)
async def upload_document(
    document_type: DocumentType,
    file: UploadFile = File(...),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    db: AsyncSession = Depends(get_db),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    document_id = str(uuid.uuid4())

    await save_file_as_data(
        upload_file=file,
        directory="raid",
        filename=document_id,
        max_file_size=50 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
            ContentType.pdf,
        ],
    )

    model_document = models_raid.Document(
        id=document_id,
        edition_id=edition.id,
        name=file.filename or document_id,
        uploaded_at=datetime.now(UTC).date(),
        type=document_type,
        validation=DocumentValidation.pending,
    )
    await cruds_raid.create_document(model_document, db)

    document_key = {
        DocumentType.idCard: "id_card_id",
        DocumentType.medicalCertificate: "medical_certificate_id",
        DocumentType.studentCard: "student_card_id",
        DocumentType.raidRules: "raid_rules_id",
        DocumentType.parentAuthorization: "parent_authorization_id",
    }[document_type]
    await cruds_raid.assign_document(
        user.id,
        edition.id,
        document_id,
        document_key,
        db,
    )
    return schemas_raid.DocumentCreation(id=document_id)


@module.router.get(
    "/raid/document/{document_id}",
    response_class=FileResponse,
    status_code=200,
)
async def read_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    document = await cruds_raid.get_document_by_id(document_id, db)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    participant = await cruds_raid.get_user_by_document_id(document_id, db)
    if not participant:
        information = await get_core_data(coredata_raid.RaidInformation, db)
        if document_id in {information.raid_rules_id, information.raid_information_id}:
            return get_file_from_data(
                default_asset="assets/pdf/default_PDF.pdf",
                directory="raid",
                filename=str(document_id),
            )
        raise HTTPException(
            status_code=404,
            detail="Participant owning the document not found.",
        )

    is_admin = await has_user_permission(user, RaidPermissions.manage_raid, db)
    if not is_admin:
        # Self or teammate can read
        user_team = await cruds_raid.get_team_by_participant_id(
            user.id,
            edition.id,
            db,
        )
        owner_team = await cruds_raid.get_team_by_participant_id(
            participant.user_id,
            edition.id,
            db,
        )
        if (
            user.id != participant.user_id
            and (user_team is None or owner_team is None or user_team.id != owner_team.id)
        ):
            raise HTTPException(
                status_code=403,
                detail="The owner of this document is not a member of your team.",
            )

    return get_file_from_data(
        default_asset="assets/pdf/default_PDF.pdf",
        directory="raid",
        filename=str(document_id),
    )


@module.router.post(
    "/raid/document/{document_id}/validate",
    status_code=204,
)
async def validate_document(
    document_id: str,
    validation: DocumentValidation,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    await cruds_raid.update_document_validation(document_id, validation, db)


# ---------------------------------------------------------------------------
# Security file
# ---------------------------------------------------------------------------


@module.router.post(
    "/raid/security_file/",
    response_model=schemas_raid.SecurityFile,
    status_code=201,
)
async def set_security_file(
    security_file: schemas_raid.SecurityFileBase,
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    """Submit or replace the security file of a participant (self or teammate)."""
    is_admin = await has_user_permission(user, RaidPermissions.manage_raid, db)
    if user.id != participant_id and not is_admin:
        user_team = await cruds_raid.get_team_by_participant_id(
            user.id,
            edition.id,
            db,
        )
        target_team = await cruds_raid.get_team_by_participant_id(
            participant_id,
            edition.id,
            db,
        )
        if user_team is None or target_team is None or user_team.id != target_team.id:
            raise HTTPException(status_code=403, detail="You are not the participant.")

    participant = await get_participant_or_404(participant_id, edition.id, db)

    if participant.security_file_id:
        await cruds_raid.update_security_file(
            security_file_id=participant.security_file_id,
            security_file=security_file,
            db=db,
        )
        existing = await cruds_raid.get_security_file_by_security_id(
            participant.security_file_id,
            db,
        )
        return existing

    model_security_file = models_raid.SecurityFile(
        id=str(uuid.uuid4()),
        edition_id=edition.id,
        allergy=security_file.allergy,
        asthma=security_file.asthma,
        intensive_care_unit=security_file.intensive_care_unit,
        intensive_care_unit_when=security_file.intensive_care_unit_when,
        ongoing_treatment=security_file.ongoing_treatment,
        sicknesses=security_file.sicknesses,
        hospitalization=security_file.hospitalization,
        surgical_operation=security_file.surgical_operation,
        trauma=security_file.trauma,
        family=security_file.family,
        emergency_person_firstname=security_file.emergency_person_firstname,
        emergency_person_name=security_file.emergency_person_name,
        emergency_person_phone=security_file.emergency_person_phone,
        file_id=security_file.file_id,
    )
    created = await cruds_raid.add_security_file(model_security_file, db)
    await cruds_raid.assign_security_file(participant_id, edition.id, created.id, db)
    return created


# ---------------------------------------------------------------------------
# Manual payment + attestation
# ---------------------------------------------------------------------------


@module.router.post(
    "/raid/participant/{user_id}/payment",
    status_code=204,
)
async def confirm_payment(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    await cruds_raid.confirm_payment(user_id, edition.id, db)


@module.router.post(
    "/raid/participant/{user_id}/t_shirt_payment",
    status_code=204,
)
async def confirm_t_shirt_payment(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    participant = await cruds_raid.get_participant_by_user_id(user_id, edition.id, db)
    if (
        not participant
        or not participant.t_shirt_size
        or participant.t_shirt_size == Size.None_
    ):
        raise HTTPException(status_code=400, detail="T shirt size not set.")
    await cruds_raid.confirm_t_shirt_payment(user_id, edition.id, db)


@module.router.post(
    "/raid/participant/{user_id}/honour",
    status_code=204,
)
async def validate_attestation_on_honour(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    if user_id != user.id:
        raise HTTPException(status_code=403, detail="You are not the participant")
    await cruds_raid.validate_attestation_on_honour(user_id, edition.id, db)


# ---------------------------------------------------------------------------
# Invite + join + kick + merge
# ---------------------------------------------------------------------------


@module.router.post(
    "/raid/teams/{team_id}/invite",
    response_model=schemas_raid.InviteToken,
    status_code=201,
)
async def create_invite_token(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    team = await cruds_raid.get_team_by_participant_id(user.id, edition.id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
    if team.id != team_id:
        raise HTTPException(status_code=403, detail="You are not in the team.")

    existing = await cruds_raid.get_invite_token_by_team_id(team_id, db)
    if existing:
        return existing

    invite_token = models_raid.InviteToken(
        id=str(uuid.uuid4()),
        edition_id=edition.id,
        team_id=team_id,
        token=get_random_string(length=10),
    )
    return await cruds_raid.create_invite_token(invite_token, db)


@module.router.post(
    "/raid/teams/join/{token}",
    status_code=204,
)
async def join_team(
    token: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    invite_token = await cruds_raid.get_invite_token_by_token(token, db)
    if not invite_token:
        raise HTTPException(status_code=404, detail="Invite token not found.")
    if invite_token.edition_id != edition.id:
        raise HTTPException(status_code=400, detail="Invite for a different edition")

    user_team = await cruds_raid.get_team_by_participant_id(user.id, edition.id, db)
    if user_team:
        if user_team.second_id:
            raise HTTPException(status_code=403, detail="You are already in a team.")
        await cruds_raid.delete_team(user_team.id, db)

    team = await cruds_raid.get_team_by_id(invite_token.team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
    if team.second_id:
        raise HTTPException(status_code=403, detail="Team is already full.")
    if team.captain_id == user.id:
        raise HTTPException(
            status_code=403,
            detail="You are already the captain of this team.",
        )

    await cruds_raid.delete_invite_token(invite_token.id, db)
    await cruds_raid.update_team_second_id(team.id, user.id, db)


@module.router.post(
    "/raid/teams/{team_id}/kick/{user_id}",
    response_model=schemas_raid.RaidTeam,
    status_code=201,
)
async def kick_team_member(
    team_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    team = await cruds_raid.get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
    if team.captain_id == user_id:
        if not team.second_id:
            raise HTTPException(
                status_code=403,
                detail="You can not kick the only member of the team.",
            )
        await cruds_raid.update_team_captain_id(team_id, team.second_id, db)
    elif team.second_id != user_id:
        raise HTTPException(status_code=404, detail="Participant not found.")
    await cruds_raid.update_team_second_id(team_id, None, db)
    return await cruds_raid.get_team_by_id(team_id, db)


@module.router.post(
    "/raid/teams/merge",
    response_model=schemas_raid.RaidTeam,
    status_code=201,
)
async def merge_teams(
    team1_id: str,
    team2_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    team1 = await cruds_raid.get_team_by_id(team1_id, db)
    team2 = await cruds_raid.get_team_by_id(team2_id, db)
    if not team1 or not team2:
        raise HTTPException(status_code=404, detail="Team not found.")
    if team1.second_id or team2.second_id:
        raise HTTPException(status_code=403, detail="One of the team is full.")
    if team1.captain_id == team2.captain_id:
        raise HTTPException(status_code=403, detail="Teams are the same.")
    new_name = f"{team1.name} & {team2.name}"
    new_difficulty = team1.difficulty if team1.difficulty == team2.difficulty else None
    new_meeting_place = (
        team1.meeting_place if team1.meeting_place == team2.meeting_place else None
    )
    new_number = (
        min(team1.number, team2.number) if team1.number and team2.number else None
    )
    team_update = schemas_raid.RaidTeamUpdate(
        name=new_name,
        difficulty=new_difficulty,
        meeting_place=new_meeting_place,
        number=new_number,
    )
    await cruds_raid.delete_team_invite_tokens(team1_id, db)
    await cruds_raid.delete_team_invite_tokens(team2_id, db)
    await cruds_raid.update_team(team1_id, team_update, db)
    await cruds_raid.update_team_second_id(team1_id, team2.captain_id, db)
    await cruds_raid.delete_team(team2_id, db)
    return await cruds_raid.get_team_by_id(team1_id, db)


# ---------------------------------------------------------------------------
# Configuration (coredata)
# ---------------------------------------------------------------------------


@module.router.get(
    "/raid/information",
    response_model=coredata_raid.RaidInformation,
    status_code=200,
)
async def get_raid_information(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
):
    return await get_core_data(coredata_raid.RaidInformation, db)


@module.router.patch(
    "/raid/information",
    status_code=204,
)
async def update_raid_information(
    raid_information: coredata_raid.RaidInformation,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    last_information = await get_core_data(coredata_raid.RaidInformation, db)
    await set_core_data(raid_information, db)
    if (
        raid_information.raid_start_date
        and raid_information.raid_start_date != last_information.raid_start_date
    ):
        participants = await cruds_raid.get_all_participants(edition.id, db)
        for participant in participants:
            birthday = participant.user.birthday if participant.user else None
            is_minor = will_birthday_be_minor_on(
                birthday=birthday,
                raid_start_date=raid_information.raid_start_date,
            )
            await cruds_raid.update_participant_minority(
                participant.user_id,
                edition.id,
                is_minor,
                db,
            )


@module.router.patch(
    "/raid/drive",
    status_code=204,
)
async def update_drive_folders(
    drive_folders: schemas_raid.RaidDriveFoldersCreation,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    schemas_folders = coredata_raid.RaidDriveFolders(
        parent_folder_id=drive_folders.parent_folder_id,
        registering_folder_id=None,
        security_folder_id=None,
    )
    await set_core_data(schemas_folders, db)


@module.router.get(
    "/raid/drive",
    response_model=schemas_raid.RaidDriveFoldersCreation,
    status_code=200,
)
async def get_drive_folders(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    return await get_core_data(coredata_raid.RaidDriveFolders, db)


@module.router.get(
    "/raid/price",
    response_model=coredata_raid.RaidPrice,
    status_code=200,
)
async def get_raid_price(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
):
    return await get_core_data(coredata_raid.RaidPrice, db)


@module.router.patch(
    "/raid/price",
    status_code=204,
)
async def update_raid_price(
    raid_price: coredata_raid.RaidPrice,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
):
    await set_core_data(raid_price, db)


# ---------------------------------------------------------------------------
# Payment URL
# ---------------------------------------------------------------------------


@module.router.get(
    "/raid/pay",
    response_model=schemas_raid.PaymentUrl,
    status_code=201,
)
async def get_payment_url(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    payment_tool: PaymentTool = Depends(get_payment_tool(HelloAssoConfigName.RAID)),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    raid_prices = await get_core_data(coredata_raid.RaidPrice, db)
    if (
        not raid_prices.student_price
        or not raid_prices.t_shirt_price
        or not raid_prices.external_price
    ):
        raise HTTPException(status_code=404, detail="Prices not set.")

    participant = await cruds_raid.get_participant_by_user_id(user.id, edition.id, db)
    if not participant:
        raise HTTPException(status_code=403, detail="You are not a participant.")
    price, checkout_name = calculate_raid_payment(participant, raid_prices)

    user_dict = {k: v for k, v in user.__dict__.items() if not k.startswith("_")}
    user_dict.pop("school", None)
    checkout = await payment_tool.init_checkout(
        module=module.root,
        checkout_amount=price,
        checkout_name=checkout_name,
        payer_user=schemas_users.CoreUser(**user_dict),
        db=db,
    )
    hyperion_error_logger.info(f"RAID: Logging Checkout id {checkout.id}")
    await cruds_raid.create_participant_checkout(
        models_raid.RaidParticipantCheckout(
            id=str(uuid.uuid4()),
            participant_user_id=user.id,
            edition_id=edition.id,
            checkout_id=str(checkout.id),
        ),
        db=db,
    )
    return schemas_raid.PaymentUrl(url=checkout.payment_url)


# ---------------------------------------------------------------------------
# Bulk downloads
# ---------------------------------------------------------------------------


@module.router.get(
    "/raid/security_files_zip",
    response_class=FileResponse,
    status_code=200,
)
async def download_security_files_zip(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    information = await get_core_data(coredata_raid.RaidInformation, db)
    zip_file_path = await get_all_security_files_zip(db, information, edition.id)
    return FileResponse(
        zip_file_path,
        media_type="application/zip",
        filename=Path(zip_file_path).name,
    )


@module.router.get(
    "/raid/team_files_zip",
    response_class=FileResponse,
    status_code=200,
)
async def download_team_files_zip(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    information = await get_core_data(coredata_raid.RaidInformation, db)
    zip_file_path = await get_all_team_files_zip(db, information, edition.id)
    return FileResponse(
        zip_file_path,
        media_type="application/zip",
        filename=Path(zip_file_path).name,
    )


# ---------------------------------------------------------------------------
# Volunteers
# ---------------------------------------------------------------------------


@module.router.post(
    "/raid/volunteers",
    response_model=schemas_raid.RaidVolunteer,
    status_code=201,
)
async def create_volunteer(
    volunteer: schemas_raid.RaidVolunteerBase,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    db: AsyncSession = Depends(get_db),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    if await cruds_raid.get_volunteer_by_user_id(user.id, edition.id, db):
        raise HTTPException(status_code=403, detail="You are already a volunteer.")
    await ensure_user_is_not_participant_in_edition(user.id, edition.id, db)

    model_volunteer = models_raid.RaidVolunteer(
        user_id=user.id,
        edition_id=edition.id,
        created_at=datetime.now(UTC),
        validated=False,
        cancelled=False,
        diet=volunteer.diet,
        allergy=volunteer.allergy,
        has_car=volunteer.has_car,
        car_seats=volunteer.car_seats,
        is_special_driver=volunteer.is_special_driver,
        is_utility_vehicle_driver=volunteer.is_utility_vehicle_driver,
        is_parcours_helper=volunteer.is_parcours_helper,
    )
    await cruds_raid.create_volunteer(model_volunteer, db)
    return await get_volunteer_or_404(user.id, edition.id, db)


@module.router.get(
    "/raid/volunteers/me",
    response_model=schemas_raid.RaidVolunteer,
    status_code=200,
)
async def get_my_volunteer(
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    db: AsyncSession = Depends(get_db),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    return await get_volunteer_or_404(user.id, edition.id, db)


@module.router.get(
    "/raid/volunteers",
    response_model=list[schemas_raid.RaidVolunteer],
    status_code=200,
)
async def list_volunteers(
    validated: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    return await cruds_raid.get_all_volunteers_by_edition(edition.id, db, validated)


@module.router.patch(
    "/raid/volunteers/{user_id}",
    status_code=204,
)
async def update_volunteer(
    user_id: str,
    volunteer_edit: schemas_raid.RaidVolunteerEdit,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    db: AsyncSession = Depends(get_db),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    is_admin = await has_user_permission(user, RaidPermissions.manage_raid, db)
    if user.id != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="You are not the volunteer.")
    existing = await get_volunteer_or_404(user_id, edition.id, db)
    if existing.validated and not is_admin:
        raise HTTPException(
            status_code=400,
            detail="Volunteer is validated; admin-only update",
        )
    values = volunteer_edit.model_dump(exclude_none=True)
    await cruds_raid.update_volunteer(user_id, edition.id, values, db)


@module.router.patch(
    "/raid/volunteers/{user_id}/validate",
    status_code=204,
)
async def validate_volunteer(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.manage_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    volunteer = await get_volunteer_or_404(user_id, edition.id, db)
    await check_volunteer_validation_consistency(volunteer, edition.id, db)
    await cruds_raid.update_volunteer_validation(user_id, edition.id, True, db)


@module.router.patch(
    "/raid/volunteers/{user_id}/cancel",
    status_code=204,
)
async def cancel_volunteer(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    is_admin = await has_user_permission(user, RaidPermissions.manage_raid, db)
    if user.id != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="You are not the volunteer.")
    await get_volunteer_or_404(user_id, edition.id, db)
    await cruds_raid.update_volunteer_cancellation(user_id, edition.id, True, db)


@module.router.delete(
    "/raid/volunteers/{user_id}",
    status_code=204,
)
async def delete_volunteer(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([RaidPermissions.access_raid]),
    ),
    edition: schemas_raid.RaidEdition = Depends(get_current_raid_edition),
):
    is_admin = await has_user_permission(user, RaidPermissions.manage_raid, db)
    if user.id != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="You are not the volunteer.")
    existing = await get_volunteer_or_404(user_id, edition.id, db)
    if existing.validated and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Cannot remove a validated volunteer (admin-only)",
        )
    await cruds_raid.delete_volunteer(user_id, edition.id, db)
