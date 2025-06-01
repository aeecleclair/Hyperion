import logging
import uuid
from datetime import UTC, date, datetime

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.google_api.google_api import DriveGoogleAPI
from app.core.groups.groups_type import AccountType, GroupType
from app.core.payment.payment_tool import PaymentTool
from app.core.users import models_users, schemas_users
from app.core.utils.config import Settings
from app.dependencies import (
    get_db,
    get_drive_file_manager,
    get_payment_tool,
    get_request_id,
    get_settings,
    is_user,
    is_user_in,
)
from app.modules.raid import coredata_raid, cruds_raid, models_raid, schemas_raid
from app.modules.raid.raid_type import DocumentType, DocumentValidation, Size
from app.modules.raid.utils.drive.drive_file_manager import DriveFileManager
from app.modules.raid.utils.utils_raid import (
    generate_teams_pdf_util,
    get_participant,
    post_update_actions,
    save_security_file,
    validate_payment,
    will_participant_be_minor_on,
)
from app.types.content_type import ContentType
from app.types.exceptions import MissingHelloAssoSlugError
from app.types.module import Module
from app.utils.tools import (
    get_core_data,
    get_file_from_data,
    get_random_string,
    is_user_member_of_any_group,
    save_file_as_data,
    set_core_data,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


module = Module(
    root="raid",
    tag="Raid",
    payment_callback=validate_payment,
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)


@module.router.get(
    "/raid/participants/{participant_id}",
    response_model=schemas_raid.Participant,
    status_code=200,
)
async def get_participant_by_id(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Get a participant by id
    """
    if participant_id != user.id and not is_user_member_of_any_group(
        user,
        [GroupType.raid_admin],
    ):
        raise HTTPException(
            status_code=403,
            detail="You can not get data of another user",
        )

    return await get_participant(participant_id, db)


@module.router.post(
    "/raid/participants",
    response_model=schemas_raid.Participant,
    status_code=201,
)
async def create_participant(
    participant: schemas_raid.ParticipantBase,
    user: models_users.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a participant
    """
    # If the user is already a participant, return an error
    if await cruds_raid.is_user_a_participant(user.id, db):
        raise HTTPException(status_code=403, detail="You are already a participant.")

    raid_information = await get_core_data(coredata_raid.RaidInformation, db)
    # If the start_date is not set, we will use January the first of next year to determine if participants
    # are minors. We can safely assume that the RAID will occurre before Jan 1 of next year

    is_minor = will_participant_be_minor_on(
        participant=participant,
        raid_start_date=raid_information.raid_start_date,
    )

    db_participant = models_raid.Participant(
        **participant.__dict__,
        id=user.id,
        is_minor=is_minor,
    )
    return await cruds_raid.create_participant(db_participant, db)


@module.router.patch(
    "/raid/participants/{participant_id}",
    status_code=204,
)
async def update_participant(
    participant_id: str,
    participant: schemas_raid.ParticipantUpdate,
    user: models_users.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Update a participant
    """
    # If the user is not a participant, return an error
    if not await cruds_raid.is_user_a_participant(participant_id, db):
        raise HTTPException(status_code=403, detail="You are not a participant.")

    # If the user is not the participant, return an error
    if not await cruds_raid.are_user_in_the_same_team(user.id, participant_id, db):
        raise HTTPException(status_code=403, detail="You are not the participant.")

    raid_information = await get_core_data(coredata_raid.RaidInformation, db)
    raid_start_date = raid_information.raid_start_date or date(
        year=datetime.now(UTC).year + 1,
        month=1,
        day=1,
    )

    # We only want to change the is_minor value if the birthday is changed
    is_minor = None
    if participant.birthday:
        is_minor = will_participant_be_minor_on(participant, raid_start_date)

    saved_participant = await get_participant(participant_id, db)

    # If the t_shirt_payment is set, we cannot remove the t_shirt_size
    if saved_participant.t_shirt_payment and participant.t_shirt_size == Size.None_:
        participant.t_shirt_size = saved_participant.t_shirt_size

    if participant.id_card_id:
        id_card_document = await cruds_raid.get_document_by_id(
            participant.id_card_id,
            db=db,
        )
        if not id_card_document:
            raise HTTPException(status_code=404, detail="Document id_card not found.")

    if participant.medical_certificate_id:
        medical_certificate_document = await cruds_raid.get_document_by_id(
            participant.medical_certificate_id,
            db=db,
        )
        if not medical_certificate_document:
            raise HTTPException(
                status_code=404,
                detail="Document medical_certificate not found.",
            )
    if participant.student_card_id:
        student_card_document = await cruds_raid.get_document_by_id(
            participant.student_card_id,
            db=db,
        )
        if not student_card_document:
            raise HTTPException(
                status_code=404,
                detail="Document student_card not found.",
            )
    if participant.raid_rules_id:
        raid_rules_document = await cruds_raid.get_document_by_id(
            participant.raid_rules_id,
            db=db,
        )
        if not raid_rules_document:
            raise HTTPException(
                status_code=404,
                detail="Document raid_rules not found.",
            )
    if participant.parent_authorization_id:
        parent_authorization_document = await cruds_raid.get_document_by_id(
            participant.parent_authorization_id,
            db=db,
        )
        if not parent_authorization_document:
            raise HTTPException(
                status_code=404,
                detail="Document parent_authorization not found.",
            )

    if participant.security_file_id:
        security_file = await cruds_raid.get_security_file_by_security_id(
            participant.security_file_id,
            db=db,
        )
        if not security_file:
            raise HTTPException(
                status_code=404,
                detail="Security_file not found.",
            )

    await cruds_raid.update_participant(participant_id, participant, is_minor, db)
    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    if team:
        await post_update_actions(
            team,
            db,
            drive_file_manager,
            settings=settings,
        )


@module.router.post(
    "/raid/teams",
    response_model=schemas_raid.Team,
    status_code=201,
)
async def create_team(
    team: schemas_raid.TeamBase,
    user: models_users.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Create a team
    """
    # If the user is not a participant, return an error
    if not await cruds_raid.is_user_a_participant(user.id, db):
        raise HTTPException(status_code=403, detail="You are not a participant.")

    # If the user already has a team, return an error
    if await cruds_raid.get_team_by_participant_id(user.id, db):
        raise HTTPException(status_code=403, detail="You already have a team.")

    db_team = models_raid.Team(
        id=str(uuid.uuid4()),
        name=team.name,
        number=None,
        captain_id=user.id,
        second_id=None,
        difficulty=None,
    )
    await cruds_raid.create_team(db_team, db)
    # We need to get the team from the db to have access to relationships
    created_team = await cruds_raid.get_team_by_id(team_id=db_team.id, db=db)
    if created_team:
        await post_update_actions(
            created_team,
            db,
            drive_file_manager,
            settings=settings,
        )
    return created_team


@module.router.post(
    "/raid/teams/generate-pdf",
    status_code=200,
)
async def generate_teams_pdf(
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
    db: AsyncSession = Depends(get_db),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    PDF are automatically generated when a team is created or updated.
    This endpoint is used to regenerate all the PDFs.
    """
    await generate_teams_pdf_util(
        db=db,
        drive_file_manager=drive_file_manager,
        settings=settings,
    )

    return "PDF generation started"


@module.router.get(
    "/raid/participants/{participant_id}/team",
    response_model=schemas_raid.Team,
    status_code=200,
)
async def get_team_by_participant_id(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Get a team by participant id
    """
    if user.id != participant_id:
        raise HTTPException(status_code=403, detail="You are not the participant.")

    # If the user is not a participant, return an error
    if not await cruds_raid.is_user_a_participant(participant_id, db):
        raise HTTPException(status_code=403, detail="You are not a participant.")

    participant_team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    # If the user does not have a team, return an error
    if not participant_team:
        raise HTTPException(status_code=404, detail="You do not have a team.")
    return participant_team


@module.router.get(
    "/raid/teams",
    response_model=list[schemas_raid.TeamPreview],
    status_code=200,
)
async def get_all_teams(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
):
    """
    Get all teams
    """
    return await cruds_raid.get_all_teams(db)


@module.router.get(
    "/raid/teams/{team_id}",
    response_model=schemas_raid.Team,
    status_code=200,
)
async def get_team_by_id(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
):
    """
    Get a team by id
    """
    return await cruds_raid.get_team_by_id(team_id, db)


@module.router.patch(
    "/raid/teams/{team_id}",
    status_code=204,
)
async def update_team(
    team_id: str,
    team: schemas_raid.TeamUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Update a team
    """
    existing_team = await cruds_raid.get_team_by_participant_id(user.id, db)
    if existing_team is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    if existing_team.id != team_id:
        raise HTTPException(status_code=403, detail="You can only edit your own team.")
    await cruds_raid.update_team(team_id, team, db)
    updated_team = await cruds_raid.get_team_by_id(team_id, db)
    if updated_team:
        await post_update_actions(
            updated_team,
            db,
            drive_file_manager,
            settings=settings,
        )


@module.router.delete(
    "/raid/teams/{team_id}",
    status_code=204,
)
async def delete_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
    settings: Settings = Depends(get_settings),
):
    """
    Delete a team
    """
    team = await cruds_raid.get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=403, detail="This team does not exists")
    await cruds_raid.delete_team_invite_tokens(team_id, db)
    await cruds_raid.delete_team(team_id, db)
    # We will try to delete PDF associated with the team from the Google Drive
    if team.file_id:
        async with DriveGoogleAPI(db, settings) as google_api:
            google_api.delete_file(team.file_id)
            if team.captain.security_file and team.captain.security_file.file_id:
                google_api.delete_file(team.captain.security_file.file_id)
            if (
                team.second
                and team.second.security_file
                and team.second.security_file.file_id
            ):
                google_api.delete_file(team.second.security_file.file_id)


@module.router.delete(
    "/raid/teams",
    status_code=204,
)
async def delete_all_teams(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
    settings: Settings = Depends(get_settings),
):
    """
    Delete all teams
    """
    # First get all teams to access their file IDs
    teams = await cruds_raid.get_all_teams(db)
    # Delete files associated with each team from Google Drive
    async with DriveGoogleAPI(db, settings) as google_api:
        for team in teams:
            # Delete team PDF
            if team.file_id:
                google_api.delete_file(team.file_id)
            # Delete captain's security file if exists
            if (
                team.captain
                and team.captain.security_file
                and team.captain.security_file.file_id
            ):
                google_api.delete_file(team.captain.security_file.file_id)
            # Delete second member's security file if exists
            if (
                team.second
                and team.second.security_file
                and team.second.security_file.file_id
            ):
                google_api.delete_file(team.second.security_file.file_id)
            # Delete team invite tokens

    await cruds_raid.delete_all_invite_tokens(db)

    # Delete all teams from the database
    await cruds_raid.delete_all_teams(db)


@module.router.post(
    "/raid/document/{document_type}",
    response_model=schemas_raid.DocumentCreation,
    status_code=201,
)
async def upload_document(
    document_type: DocumentType,
    file: UploadFile = File(...),
    user: models_users.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document
    """
    document_id = str(uuid.uuid4())

    await save_file_as_data(
        upload_file=file,
        directory="raid",
        filename=document_id,
        max_file_size=50 * 1024 * 1024,  # TODO : Change this value
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
            ContentType.pdf,
        ],  # TODO : Change this value
    )

    model_document = models_raid.Document(
        uploaded_at=datetime.now(UTC).date(),
        validation=DocumentValidation.pending,
        id=document_id,
        name=file.filename or document_id,
        type=document_type,
    )

    await cruds_raid.create_document(model_document, db)
    document_key = ""
    match document_type:
        case DocumentType.idCard:
            document_key = "id_card_id"
        case DocumentType.medicalCertificate:
            document_key = "medical_certificate_id"
        case DocumentType.studentCard:
            document_key = "student_card_id"
        case DocumentType.raidRules:
            document_key = "raid_rules_id"
        case DocumentType.parentAuthorization:
            document_key = "parent_authorization_id"
    await cruds_raid.assign_document(user.id, document_id, document_key, db)

    return schemas_raid.DocumentCreation(id=document_id)


@module.router.get(
    "/raid/document/{document_id}",
    response_class=FileResponse,
    status_code=200,
)
async def read_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Read a document
    """

    document = await cruds_raid.get_document_by_id(document_id, db)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    participant = await cruds_raid.get_user_by_document_id(document_id, db)
    if not participant:
        # The document can be a global document
        information = await get_core_data(coredata_raid.RaidInformation, db)
        if document_id in {information.raid_rules_id, information.raid_information_id}:
            return get_file_from_data(
                default_asset="assets/documents/raid_rules.pdf",
                directory="raid",
                filename=str(document_id),
            )
        raise HTTPException(
            status_code=404,
            detail="Participant owning the document not found.",
        )

    if not await cruds_raid.are_user_in_the_same_team(
        user.id,
        participant.id,
        db,
    ) and not is_user_member_of_any_group(user, [GroupType.raid_admin]):
        raise HTTPException(
            status_code=403,
            detail="The owner of this document is not a member of your team.",
        )

    return get_file_from_data(
        default_asset="assets/images/default_advert.png",  # TODO: get a default document
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
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Validate a document
    """
    await cruds_raid.update_document_validation(document_id, validation, db)
    team = await cruds_raid.get_team_by_participant_id(user.id, db)
    if team:
        await post_update_actions(
            team,
            db,
            drive_file_manager,
            settings=settings,
        )


@module.router.post(
    "/raid/security_file/",
    response_model=schemas_raid.SecurityFile,
    status_code=201,
)
async def set_security_file(
    security_file: schemas_raid.SecurityFileBase,
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Confirm security file
    """
    team = await cruds_raid.get_team_if_users_in_the_same_team(
        user.id,
        participant_id,
        db,
    )
    if team is None:
        raise HTTPException(status_code=403, detail="You are not the participant.")

    participant = await get_participant(participant_id, db)
    if participant is None:
        raise HTTPException(status_code=403, detail="The participant does not exist")

    if participant.security_file_id:
        # The participant already has a security file
        # We want to delete it to replace it by the new one
        await cruds_raid.update_security_file(
            security_file_id=participant.security_file_id,
            security_file=security_file,
            db=db,
        )

    model_security_file = models_raid.SecurityFile(
        id=str(uuid.uuid4()),
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
    created_security_file = await cruds_raid.add_security_file(model_security_file, db)
    await cruds_raid.assign_security_file(participant_id, created_security_file.id, db)

    information = await get_core_data(coredata_raid.RaidInformation, db)
    await save_security_file(
        participant,
        information,
        team.number,
        db,
        drive_file_manager,
        settings,
    )
    await post_update_actions(
        team,
        db,
        drive_file_manager,
        settings=settings,
    )
    return created_security_file


@module.router.post(
    "/raid/participant/{participant_id}/payment",
    status_code=204,
)
async def confirm_payment(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Confirm payment manually
    """
    await cruds_raid.confirm_payment(participant_id, db)
    team = await cruds_raid.get_team_by_participant_id(
        participant_id,
        db,
    )
    if team:
        await post_update_actions(
            team,
            db,
            drive_file_manager,
            settings=settings,
        )


@module.router.post(
    "/raid/participant/{participant_id}/t_shirt_payment",
    status_code=204,
)
async def confirm_t_shirt_payment(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Confirm T shirt payment
    """
    participant = await cruds_raid.get_participant_by_id(participant_id, db)
    if (
        not participant
        or not participant.t_shirt_size
        or participant.t_shirt_size == Size.None_
    ):
        raise HTTPException(status_code=400, detail="T shirt size not set.")
    await cruds_raid.confirm_t_shirt_payment(participant_id, db)
    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    if team:
        await post_update_actions(
            team,
            db,
            drive_file_manager,
            settings=settings,
        )


@module.router.post(
    "/raid/participant/{participant_id}/honour",
    status_code=204,
)
async def validate_attestation_on_honour(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Validate attestation on honour
    """
    if participant_id != user.id:
        raise HTTPException(status_code=403, detail="You are not the participant")
    await cruds_raid.validate_attestation_on_honour(participant_id, db)
    team = await cruds_raid.get_team_by_participant_id(participant_id, db)
    if team:
        await post_update_actions(
            team,
            db,
            drive_file_manager,
            settings=settings,
        )


@module.router.post(
    "/raid/teams/{team_id}/invite",
    response_model=schemas_raid.InviteToken,
    status_code=201,
)
async def create_invite_token(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Create an invite token
    """
    team = await cruds_raid.get_team_by_participant_id(user.id, db)

    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")

    if team.id != team_id:
        raise HTTPException(status_code=403, detail="You are not in the team.")

    existing_invite_token = await cruds_raid.get_invite_token_by_team_id(team_id, db)

    if existing_invite_token:
        return existing_invite_token

    invite_token = models_raid.InviteToken(
        id=str(uuid.uuid4()),
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
    user: models_users.CoreUser = Depends(is_user()),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Join a team
    """
    invite_token = await cruds_raid.get_invite_token_by_token(token, db)

    if not invite_token:
        raise HTTPException(status_code=404, detail="Invite token not found.")

    user_team = await cruds_raid.get_team_by_participant_id(user.id, db)

    # An user that is in a team without a second participant will quit its teams to joint the other
    # If there are already two participants in the user's team, we want to raise an error
    if user_team:
        if user_team.second_id:
            raise HTTPException(status_code=403, detail="You are already in a team.")

        if user_team.file_id:
            async with DriveGoogleAPI(db, settings) as google_api:
                google_api.delete_file(user_team.file_id)
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

    await cruds_raid.update_team_second_id(team.id, user.id, db)
    await post_update_actions(
        team,
        db,
        drive_file_manager,
        settings=settings,
    )
    await cruds_raid.delete_invite_token(invite_token.id, db)


@module.router.post(
    "/raid/teams/{team_id}/kick/{participant_id}",
    response_model=schemas_raid.Team,
    status_code=201,
)
async def kick_team_member(
    team_id: str,
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Leave a team
    """
    team = await cruds_raid.get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
    if team.captain_id == participant_id:
        if not team.second_id:
            raise HTTPException(
                status_code=403,
                detail="You can not kick the only member of the team.",
            )
        await cruds_raid.update_team_captain_id(
            team_id,
            team.second_id,
            db,
        )
    elif team.second_id != participant_id:
        raise HTTPException(status_code=404, detail="Participant not found.")
    await cruds_raid.update_team_second_id(team_id, None, db)
    await post_update_actions(
        team,
        db,
        drive_file_manager,
        settings=settings,
    )
    return await cruds_raid.get_team_by_id(team_id, db)


@module.router.post(
    "/raid/teams/merge",
    response_model=schemas_raid.Team,
    status_code=201,
)
async def merge_teams(
    team1_id: str,
    team2_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Merge two teams
    """
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
    team_update: schemas_raid.TeamUpdate = schemas_raid.TeamUpdate(
        name=new_name,
        difficulty=new_difficulty,
        meeting_place=new_meeting_place,
        number=new_number,
    )
    await cruds_raid.update_team(
        team1_id,
        team_update,
        db,
    )
    await cruds_raid.update_team_second_id(team1_id, team2.captain_id, db)
    await cruds_raid.delete_team(team2_id, db)
    if team2.file_id:
        async with DriveGoogleAPI(db, settings) as google_api:
            google_api.delete_file(team2.file_id)
    await post_update_actions(
        team1,
        db,
        drive_file_manager,
        settings=settings,
    )
    return await cruds_raid.get_team_by_id(team1_id, db)


@module.router.get(
    "/raid/information",
    response_model=coredata_raid.RaidInformation,
    status_code=200,
)
async def get_raid_information(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Get raid information
    """
    return await get_core_data(coredata_raid.RaidInformation, db)


@module.router.patch(
    "/raid/information",
    status_code=204,
)
async def update_raid_information(
    raid_information: coredata_raid.RaidInformation,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Update raid information
    """
    # Checking the last saved information is a temporary fix for core data not supporting exclude None on update
    last_information = await get_core_data(coredata_raid.RaidInformation, db)
    await set_core_data(raid_information, db)
    if (
        raid_information.raid_start_date
        and raid_information.raid_start_date != last_information.raid_start_date
    ):
        participants = await cruds_raid.get_all_participants(db)
        for participant in participants:
            is_minor = will_participant_be_minor_on(
                participant=participant,
                raid_start_date=raid_information.raid_start_date,
            )
            await cruds_raid.update_participant_minority(participant.id, is_minor, db)
    if (
        (
            raid_information.president
            and raid_information.president != last_information.president
        )
        or (
            raid_information.rescue
            and raid_information.rescue != last_information.rescue
        )
        or (
            raid_information.security_responsible
            and raid_information.security_responsible
            != last_information.security_responsible
        )
        or (
            raid_information.volunteer_responsible
            and raid_information.volunteer_responsible
            != last_information.volunteer_responsible
        )
    ):
        participants = await cruds_raid.get_all_participants(db)
        information = await get_core_data(coredata_raid.RaidInformation, db)
        for participant in participants:
            team = await cruds_raid.get_team_by_participant_id(participant.id, db)
            if team:
                await save_security_file(
                    participant,
                    information,
                    team.number,
                    db,
                    drive_file_manager,
                    settings,
                )


@module.router.patch(
    "/raid/drive",
    status_code=204,
)
async def update_drive_folders(
    drive_folders: schemas_raid.RaidDriveFoldersCreation,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
    drive_file_manager: DriveFileManager = Depends(get_drive_file_manager),
    settings: Settings = Depends(get_settings),
):
    """
    Update drive folders
    """
    schemas_folders = await get_core_data(coredata_raid.RaidDriveFolders, db)
    schemas_folders = coredata_raid.RaidDriveFolders(
        parent_folder_id=drive_folders.parent_folder_id,
        registering_folder_id=None,
        security_folder_id=None,
    )
    await set_core_data(schemas_folders, db)
    await drive_file_manager.init_folders(db=db, settings=settings)


@module.router.get(
    "/raid/drive",
    response_model=schemas_raid.RaidDriveFoldersCreation,
    status_code=200,
)
async def get_drive_folders(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
):
    """
    Get drive folders
    """
    return await get_core_data(coredata_raid.RaidDriveFolders, db)


@module.router.get(
    "/raid/price",
    response_model=coredata_raid.RaidPrice,
    status_code=200,
)
async def get_raid_price(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Get raid price
    """
    return await get_core_data(coredata_raid.RaidPrice, db)


@module.router.patch(
    "/raid/price",
    status_code=204,
)
async def update_raid_price(
    raid_price: coredata_raid.RaidPrice,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.raid_admin)),
):
    """
    Update raid price
    """
    await set_core_data(raid_price, db)


@module.router.get(
    "/raid/pay",
    response_model=schemas_raid.PaymentUrl,
    status_code=201,
)
async def get_payment_url(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
    payment_tool: PaymentTool = Depends(get_payment_tool),
):
    """
    Get payment url
    """
    if settings.HELLOASSO_SLUG is None:
        raise MissingHelloAssoSlugError("HELLOASSO_SLUG")

    raid_prices = await get_core_data(coredata_raid.RaidPrice, db)
    if (
        not raid_prices.student_price
        or not raid_prices.t_shirt_price
        or not raid_prices.external_price
    ):
        raise HTTPException(status_code=404, detail="Prices not set.")

    price = 0
    checkout_name = ""
    participant = await cruds_raid.get_participant_by_id(user.id, db)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found.")

    if participant.validation_progress != 100:
        raise HTTPException(
            status_code=400,
            detail="You must complete your registration before paying.",
        )

    if not participant.payment:
        if (
            participant.student_card is not None
            and participant.student_card.validation == DocumentValidation.accepted
        ):
            price += raid_prices.student_price
            checkout_name = "Inscription Raid - Tarif étudiant"
        else:
            price += raid_prices.external_price
            checkout_name = "Inscription Raid - Tarif externe"
    if (
        participant.t_shirt_size
        and participant.t_shirt_size != Size.None_
        and not participant.t_shirt_payment
    ):
        price += raid_prices.t_shirt_price
        if not participant.payment:
            checkout_name += " + "
        checkout_name += "T Shirt taille" + participant.t_shirt_size.value
    user_dict = user.__dict__
    user_dict.pop("school", None)
    checkout = await payment_tool.init_checkout(
        module=module.root,
        helloasso_slug=settings.HELLOASSO_SLUG,
        checkout_amount=price,
        checkout_name=checkout_name,
        redirection_uri=settings.RAID_PAYMENT_REDIRECTION_URL or "",
        payer_user=schemas_users.CoreUser(**user_dict),
        db=db,
    )
    hyperion_error_logger.info(f"RAID: Logging Checkout id {checkout.id}")
    await cruds_raid.create_participant_checkout(
        models_raid.ParticipantCheckout(
            id=str(uuid.uuid4()),
            participant_id=user.id,
            # TODO: use UUID
            checkout_id=str(checkout.id),
        ),
        db=db,
    )
    return schemas_raid.PaymentUrl(
        url=checkout.payment_url,
    )
