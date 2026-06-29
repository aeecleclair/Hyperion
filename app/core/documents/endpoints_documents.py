import asyncio
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.documents import cruds_documents, schemas_documents
from app.core.documents.documenso_api_wrapper import (
    DocumensoAPIWrapper,
    DocumensoConfiguration,
)
from app.core.documents.exceptions_documents import (
    ElementTeamNotFoundError,
    ElementTemplateNotFoundError,
    MissingDocumensoURLError,
)
from app.core.documents.types_documenso import (
    DocumensoWebhook,
    DocumentCompletedPayload,
    DocumentRejectedPayload,
    DocumentStatus,
    TemplateCreatedPayload,
    TemplateDeletedPayload,
    TemplateUpdatedPayload,
    WebhookEvent,
)
from app.core.documents.utils_documents import (
    handle_document_callback,
    handle_template_creation_webhook,
    use_template_for_a_recipient,
)
from app.core.groups.groups_type import GroupType
from app.core.users import cruds_users, schemas_users
from app.core.utils.config import Settings
from app.dependencies import (
    get_db,
    get_settings,
    is_user,
    is_user_in,
)
from app.types.module import CoreModule
from app.utils.tools import is_user_member_of_any_group

router = APIRouter(tags=["Documents"])

core_module = CoreModule(
    root="documents",
    tag="Documents",
    router=router,
    factory=None,
)


def _configure_documenso_api_wrapper(
    team: schemas_documents.Team,
    settings: Settings,
) -> DocumensoAPIWrapper:
    if settings.DOCUMENSO_URL is None:
        raise MissingDocumensoURLError()
    return DocumensoAPIWrapper(
        configuration=DocumensoConfiguration(
            api_key=team.api_key,
            documenso_url=settings.DOCUMENSO_URL,
        ),
    )


# region: Teams


@router.get(
    "/documents/teams/",
    response_model=list[schemas_documents.Team],
    status_code=200,
)
async def read_teams(
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Return all document teams.

    **This endpoint is only usable by administrators**
    """

    return await cruds_documents.get_teams(db)


@router.get(
    "/documents/teams/me",
    response_model=list[schemas_documents.TeamComplete],
    status_code=200,
)
async def read_user_teams(
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    """
    Return the document teams associated with the current user's groups.
    """

    return await cruds_documents.get_teams_by_group_ids(
        db=db,
        group_ids=[g.id for g in user.groups],
    )


@router.post(
    "/documents/teams/",
    response_model=schemas_documents.Team,
    status_code=201,
)
async def create_team(
    team_base: schemas_documents.TeamBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
    settings: Settings = Depends(get_settings),
):
    """
    Create a new document team.

    **This endpoint is only usable by administrators**
    """

    if await cruds_documents.get_team_by_name(db=db, name=team_base.name) is not None:
        raise HTTPException(
            status_code=400,
            detail=f"A team with the name {team_base.name} already exists",
        )
    if (
        await cruds_documents.get_team_by_group_id(db=db, group_id=team_base.group_id)
        is not None
    ):
        raise HTTPException(
            status_code=400,
            detail=f"A team for the group {team_base.group_id} already exists",
        )

    team = schemas_documents.Team(
        id=uuid.uuid4(),
        team_id=team_base.team_id,
        group_id=team_base.group_id,
        name=team_base.name,
        api_key=team_base.api_key,
    )

    documenso = _configure_documenso_api_wrapper(team, settings)
    try:
        await documenso.find_folders()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to Documenso with the provided API key: {e}",
        )

    await cruds_documents.create_team(team=team, db=db)
    return team


@router.patch(
    "/documents/teams/{team_id}",
    status_code=204,
)
async def update_team(
    team_id: uuid.UUID,
    team_update: schemas_documents.TeamUpdate,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
    settings: Settings = Depends(get_settings),
):
    """
    Update a document team.

    **This endpoint is only usable by administrators**
    """

    db_team = await cruds_documents.get_team_by_id(db=db, team_id=team_id)
    if db_team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    if team_update.name and team_update.name != db_team.name:
        if (
            await cruds_documents.get_team_by_name(db=db, name=team_update.name)
            is not None
        ):
            raise HTTPException(
                status_code=400,
                detail=f"A team with the name {team_update.name} already exists",
            )
    if team_update.group_id and team_update.group_id != db_team.group_id:
        if (
            await cruds_documents.get_team_by_group_id(
                db=db,
                group_id=team_update.group_id,
            )
            is not None
        ):
            raise HTTPException(
                status_code=400,
                detail=f"A team for the group {team_update.group_id} already exists",
            )

    documenso = _configure_documenso_api_wrapper(db_team, settings)
    try:
        await documenso.find_folders()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to Documenso with the provided API key: {e}",
        )

    await cruds_documents.update_team(db=db, team_id=team_id, team_update=team_update)


@router.delete(
    "/documents/teams/{team_id}",
    status_code=204,
)
async def delete_team(
    team_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a document team.

    **This endpoint is only usable by administrators**
    """

    db_team = await cruds_documents.get_team_by_id(db=db, team_id=team_id)
    if db_team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    await cruds_documents.delete_team(db=db, team_id=team_id)


# endregion: Teams
# region: Templates


@router.get(
    "/documents/teams/{team_id}/templates/",
    response_model=list[schemas_documents.Template],
    status_code=200,
)
async def read_team_templates(
    team_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    """
    Return all templates for a given document team.

    **This endpoint is only usable by the group that owns the team**
    """
    team = await cruds_documents.get_team_by_id(db=db, team_id=team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    if not is_user_member_of_any_group(user, [team.group_id]):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view templates for this team",
        )

    return await cruds_documents.get_team_templates(db=db, team_id=team_id)


@router.get(
    "/documents/templates/{template_id}",
    response_model=schemas_documents.TemplateComplete,
    status_code=200,
)
async def read_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    """
    Return a single template by id.

    **This endpoint is only usable by the group that owns the team linked to this template**
    """

    db_template = await cruds_documents.get_template_by_id(
        db=db,
        template_id=template_id,
    )
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    if not is_user_member_of_any_group(user, [db_template.team.group_id]):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this template",
        )
    return db_template


@router.patch(
    "/documents/templates/{template_id}",
    status_code=204,
)
async def update_template(
    template_id: uuid.UUID,
    template_update: schemas_documents.TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    """
    Update the destination folder of a template.

    **This endpoint is only usable by the group that owns the team linked to this template**
    """

    db_template = await cruds_documents.get_template_by_id(
        db=db,
        template_id=template_id,
    )
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    db_team = await cruds_documents.get_team_by_id(db=db, team_id=db_template.team_id)
    if db_team is None:
        raise ElementTeamNotFoundError(team_id=db_template.team_id)

    # Ensure the caller belongs to the group that owns this team
    if not is_user_member_of_any_group(user, [db_team.group_id]):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this template",
        )

    await cruds_documents.update_template(
        db=db,
        template_id=template_id,
        template_update=template_update,
    )


@router.post(
    "/documents/templates/{template_id}/documents/",
    response_model=schemas_documents.TemplateUseResponse,
    status_code=201,
)
async def use_template(
    template_id: uuid.UUID,
    recipient_list: schemas_documents.TemplateUse,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
):
    """
    Generate a new document from a template for a given user.
    Uses the Documenso API to create the signing request and stores the signing token.

    **This endpoint is only usable by members of the group that owns the team linked to this template**
    """

    db_template = await cruds_documents.get_template_by_id(
        db=db,
        template_id=template_id,
    )
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    if db_template.deleted:
        raise HTTPException(status_code=400, detail="Template has been deleted")

    db_team = await cruds_documents.get_team_by_id(db=db, team_id=db_template.team_id)
    if db_team is None:
        raise ElementTeamNotFoundError(team_id=db_template.team_id)

    if not is_user_member_of_any_group(user, [db_team.group_id]):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to use this template",
        )

    documenso = _configure_documenso_api_wrapper(db_team, settings)

    destination_folder_id = db_template.document_directory_id
    if destination_folder_id is None:
        raise HTTPException(
            status_code=400,
            detail="No destination folder configured for this template",
        )

    errors: dict[str, str] = {}
    users = await cruds_users.get_users_by_emails(
        db=db,
        emails=recipient_list.recipients,
    )
    found_emails = [user.email for user in users]
    for email in recipient_list.recipients:
        if email not in found_emails:
            errors[email] = "User not found"

    # Retrieve the target user to fill in the recipient fields
    documents = await asyncio.gather(
        *[
            use_template_for_a_recipient(
                recipient=user,
                template=db_template,
                destination_folder_id=destination_folder_id,
                documenso=documenso,
                db=db,
                module="documents",
                errors=errors,
            )
            for user in users
        ],
    )

    return schemas_documents.TemplateUseResponse(
        errors=errors,
        documents=[doc for doc in documents if doc is not None],
    )


# endregion: Templates
# region: Documents


@router.get(
    "/documents/me/",
    response_model=list[schemas_documents.Document],
    status_code=200,
)
async def read_my_documents(
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    """
    Return all documents assigned to the current user.
    The signing token is never included in this listing.
    """

    return await cruds_documents.get_documents_by_user_id(db=db, user_id=user.id)


@router.get(
    "/documents/{document_id}/token",
    response_model=schemas_documents.DocumentWithToken,
    status_code=200,
)
async def read_my_document_token(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    """
    Return the document with the signing token for a specific document.
    Only the user the document is addressed to may retrieve it.
    """

    db_document = await cruds_documents.get_document_with_token_by_id(
        db=db,
        document_id=document_id,
    )
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if db_document.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    return db_document


@router.get(
    "/documents/{document_id}/download",
    status_code=200,
    response_class=StreamingResponse,
)
async def download_document_file(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
):
    """
    Download the file of a specific document.
    Only the user the document is addressed to or a group administrator may download it.
    """

    db_document = await cruds_documents.get_document_by_id(
        db=db,
        document_id=document_id,
    )
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if db_document.status != DocumentStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Document is not completed and cannot be downloaded",
        )
    db_template = await cruds_documents.get_template_by_id(
        db=db,
        template_id=db_document.template_id,
    )
    if db_template is None:
        raise ElementTemplateNotFoundError(template_id=db_document.template_id)

    db_team = await cruds_documents.get_team_by_id(db=db, team_id=db_template.team_id)
    if db_team is None:
        raise ElementTeamNotFoundError(team_id=db_template.team_id)

    if db_document.user_id != user.id and not is_user_member_of_any_group(
        user,
        [db_team.group_id],
    ):
        raise HTTPException(status_code=403, detail="Access forbidden")

    documenso = _configure_documenso_api_wrapper(db_team, settings=settings)
    file_content = await documenso.download_document(
        document_id=db_document.documenso_id,
    )

    return StreamingResponse(
        BytesIO(file_content.result),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={db_document.name}.pdf",
        },
    )


@router.get(
    "/documents/templates/{template_id}/documents/",
    response_model=list[schemas_documents.DocumentComplete],
    status_code=200,
)
async def read_template_documents(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    """
    Return all documents generated from a given template

    **This endpoint is only usable by the group that owns the team linked to this template**
    """

    db_template = await cruds_documents.get_template_by_id(
        db=db,
        template_id=template_id,
    )
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    db_team = await cruds_documents.get_team_by_id(db=db, team_id=db_template.team_id)
    if db_team is None:
        raise ElementTeamNotFoundError(team_id=db_template.team_id)
    if not is_user_member_of_any_group(user, [db_team.group_id]):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view documents for this template",
        )

    return await cruds_documents.get_documents_by_template_id(
        db=db,
        template_id=template_id,
    )


# endregion: Documents
# region: Webhook


@router.post(
    "/documents/webhook/",
    status_code=200,
)
async def documenso_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Webhook endpoint called by Documenso.
    Handles: TEMPLATE_CREATED, TEMPLATE_UPDATED, TEMPLATE_DELETED,
             DOCUMENT_COMPLETED, DOCUMENT_REJECTED.
    """
    if settings.DOCUMENSO_SECRET:
        headers = request.headers
        documenso_secret = headers.get("X-Documenso-Secret")
        if documenso_secret is None or documenso_secret != settings.DOCUMENSO_SECRET:
            raise HTTPException(status_code=403, detail="Invalid Documenso signature")

    raw_body = await request.json()

    try:
        adapter: TypeAdapter[DocumensoWebhook] = TypeAdapter(DocumensoWebhook)
        webhook = adapter.validate_python(raw_body)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing payload: {e}.\nBody: {raw_body}",
        )

    match webhook.event:
        case WebhookEvent.TEMPLATE_CREATED:
            creation_payload: TemplateCreatedPayload = webhook.payload
            await handle_template_creation_webhook(payload=creation_payload, db=db)

        case WebhookEvent.TEMPLATE_UPDATED:
            update_payload: TemplateUpdatedPayload = webhook.payload
            template = await cruds_documents.get_template_by_documenso_id(
                db=db,
                documenso_id=update_payload.id,
            )
            if template is None:
                return
            await cruds_documents.update_template(
                db=db,
                template_id=template.id,
                template_update=schemas_documents.TemplateDocumensoUpdate(
                    name=update_payload.title,
                ),
            )

        case WebhookEvent.TEMPLATE_DELETED:
            deletion_payload: TemplateDeletedPayload = webhook.payload
            template = await cruds_documents.get_template_by_documenso_id(
                db=db,
                documenso_id=deletion_payload.id,
            )
            if template is None:
                return
            await cruds_documents.update_template(
                db=db,
                template_id=template.id,
                template_update=schemas_documents.TemplateDocumensoUpdate(
                    deleted=True,
                ),
            )

        case WebhookEvent.DOCUMENT_COMPLETED:
            completion_payload: DocumentCompletedPayload = webhook.payload
            if completion_payload.external_id is None:
                return
            document_id = uuid.UUID(completion_payload.external_id)
            document = await cruds_documents.get_document_by_id(
                db=db,
                document_id=document_id,
            )
            if document is None:
                return
            if document.status != DocumentStatus.PENDING:
                return

            await cruds_documents.update_document(
                db=db,
                document_id=document_id,
                status=DocumentStatus.COMPLETED,
            )

            await handle_document_callback(
                document_module=document.module,
                document_id=document_id,
                status=DocumentStatus.COMPLETED,
                db=db,
            )

        case WebhookEvent.DOCUMENT_REJECTED:
            rejection_payload: DocumentRejectedPayload = webhook.payload
            if rejection_payload.external_id is None:
                return
            document_id = uuid.UUID(rejection_payload.external_id)
            document = await cruds_documents.get_document_by_id(
                db=db,
                document_id=document_id,
            )
            if document is None:
                return
            if document.status != DocumentStatus.PENDING:
                return

            await cruds_documents.update_document(
                db=db,
                document_id=uuid.UUID(rejection_payload.external_id),
                status=DocumentStatus.REJECTED,
            )

            await handle_document_callback(
                document_module=document.module,
                document_id=document_id,
                status=DocumentStatus.REJECTED,
                db=db,
            )


# endregion: Webhook
