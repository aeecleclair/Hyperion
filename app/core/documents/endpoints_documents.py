import uuid
from datetime import UTC, datetime

from documenso_sdk import TemplateCreateDocumentFromTemplateRecipientRequest
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.documents import cruds_documents, schemas_documents
from app.core.documents.documenso_tool import DocumensoConfiguration, DocumensoTool
from app.core.documents.types_documenso import (
    DocumentStatus,
    WebhookEvent,
    parse_webhook,
)
from app.core.groups.groups_type import GroupType
from app.core.users import cruds_users, schemas_users
from app.dependencies import (
    get_db,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_documenso_tool(team: schemas_documents.Team) -> DocumensoTool:
    return DocumensoTool(
        configuration=DocumensoConfiguration(
            api_key=team.api_key,
            documenso_url=team.documenso_url,
        ),
    )


# ---------------------------------------------------------------------------
# Teams — CRUD
# ---------------------------------------------------------------------------


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
    "/documents/teams/{team_id}",
    response_model=schemas_documents.Team,
    status_code=200,
)
async def read_team(
    team_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Return a document team by id.

    **This endpoint is only usable by administrators**
    """

    db_team = await cruds_documents.get_team_by_id(db=db, team_id=team_id)
    if db_team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return db_team


@router.post(
    "/documents/teams/",
    response_model=schemas_documents.Team,
    status_code=201,
)
async def create_team(
    team_base: schemas_documents.TeamBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
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

    team = schemas_documents.Team(
        id=uuid.uuid4(),
        team_id=uuid.uuid4(),
        group_id=team_base.group_id,
        name=team_base.name,
        api_key=team_base.api_key,
        documenso_url=team_base.documenso_url,
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


# ---------------------------------------------------------------------------
# Templates — GET + PATCH (directory only)
# ---------------------------------------------------------------------------


@router.get(
    "/documents/templates/",
    response_model=list[schemas_documents.Template],
    status_code=200,
)
async def read_templates(
    team_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Return all non-deleted templates, optionally filtered by team.

    **This endpoint is only usable by administrators**
    """

    return await cruds_documents.get_templates(db=db, team_id=team_id)


@router.get(
    "/documents/templates/{template_id}",
    response_model=schemas_documents.Template,
    status_code=200,
)
async def read_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Return a single template by id.

    **This endpoint is only usable by administrators**
    """

    db_template = await cruds_documents.get_template_by_id(
        db=db,
        template_id=template_id,
    )
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")
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
    Only the group that owns the team linked to this template may call this.

    **This endpoint is only usable by group administrators**
    """

    db_template = await cruds_documents.get_template_by_id(
        db=db,
        template_id=template_id,
    )
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    db_team = await cruds_documents.get_team_by_id(db=db, team_id=db_template.team_id)
    if db_team is None:
        raise HTTPException(status_code=404, detail="Team not found")

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


# ---------------------------------------------------------------------------
# Documents — GET + POST (generate from template)
# ---------------------------------------------------------------------------


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
    "/documents/me/{document_id}/token",
    response_model=schemas_documents.DocumentComplete,
    status_code=200,
)
async def read_my_document_token(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user()),
):
    """
    Return the signing token for a specific document.
    Only the user the document is addressed to may retrieve it.
    """

    db_document = await cruds_documents.get_document_by_id(
        db=db,
        document_id=document_id,
    )
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Strict ownership check — no other user must see this token
    if db_document.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")


@router.get(
    "/documents/templates/{template_id}/documents/",
    response_model=list[schemas_documents.Document],
    status_code=200,
)
async def read_template_documents(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Return all documents generated from a given template (admin monitoring view).

    **This endpoint is only usable by administrators**
    """

    db_template = await cruds_documents.get_template_by_id(
        db=db,
        template_id=template_id,
    )
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    return await cruds_documents.get_documents_by_template_id(
        db=db,
        template_id=template_id,
    )


class DocumentCreateRequest(schemas_documents.DocumentBase):
    """Request body for document generation — wraps base fields."""


@router.post(
    "/documents/",
    response_model=schemas_documents.Document,
    status_code=201,
)
async def create_document(
    document_request: DocumentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: schemas_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Generate a new document from a template for a given user.
    Uses the Documenso API to create the signing request and stores the signing token.

    **This endpoint is only usable by group administrators**
    """

    db_template = await cruds_documents.get_template_by_id(
        db=db,
        template_id=document_request.template_id,
    )
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    if db_template.deleted:
        raise HTTPException(status_code=400, detail="Template has been deleted")

    db_team = await cruds_documents.get_team_by_id(db=db, team_id=db_template.team_id)
    if db_team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    if not is_user_member_of_any_group(user, [db_team.group_id]):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to generate a document from this template",
        )

    documenso = _build_documenso_tool(db_team)

    destination_folder_id = db_template.document_directory_id
    if destination_folder_id is None:
        raise HTTPException(
            status_code=400,
            detail="No destination folder configured for this template",
        )

    # Retrieve the target user to fill in the recipient fields

    target_user = await cruds_users.get_user_by_id(
        db=db,
        user_id=document_request.user_id,
    )
    if target_user is None:
        raise HTTPException(status_code=404, detail="Target user not found")
    document_id = uuid.uuid4()
    documenso_response = await documenso.use_template(
        template_id=float(db_template.documenso_id),
        external_id=document_id,
        recipients=[
            TemplateCreateDocumentFromTemplateRecipientRequest(
                id=1,
                name=f"{target_user.firstname} {target_user.name}",
                email=target_user.email,
            ),
        ],
        destination_folder_id=destination_folder_id,
    )

    # Extract the signing token from the first (and only) recipient
    if not documenso_response.recipients:
        raise HTTPException(
            status_code=502,
            detail="Documenso did not return any recipient for the generated document",
        )

    signing_token = documenso_response.recipients[0].token

    document = schemas_documents.DocumentComplete(
        id=document_id,
        template_id=document_request.template_id,
        name=document_request.name,
        module=document_request.module,
        user_id=document_request.user_id,
        signing_token=signing_token,
        status=DocumentStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    await cruds_documents.create_document(document=document, db=db)

    return schemas_documents.Document(
        id=document.id,
        template_id=document.template_id,
        name=document.name,
        user_id=document.user_id,
        module=document.module,
        status=document.status,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


# ---------------------------------------------------------------------------
# Webhook — handles Documenso events
# ---------------------------------------------------------------------------


@router.post(
    "/documents/webhook/",
    status_code=204,
)
async def documenso_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook endpoint called by Documenso.
    Handles: TEMPLATE_CREATED, TEMPLATE_UPDATED, TEMPLATE_DELETED,
             DOCUMENT_COMPLETED, DOCUMENT_REJECTED.
    """

    raw_body = await request.json()

    try:
        webhook = parse_webhook(raw_body)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid Documenso webhook payload")

    match webhook.event:
        case WebhookEvent.TEMPLATE_CREATED:
            payload = webhook.payload

            # We need to identify which team owns this template via its Documenso team_id
            if payload.team_id is None:
                # Template not associated with any team — ignore
                return

            # Find the internal team whose documenso team_id matches
            all_teams = await cruds_documents.get_teams(db=db)
            owning_team = next(
                (t for t in all_teams if str(t.team_id) == str(payload.team_id)),
                None,
            )
            if owning_team is None:
                # Unknown team — ignore silently
                return

            template = schemas_documents.Template(
                id=uuid.uuid4(),
                documenso_id=str(payload.id),
                name=payload.title,
                team_id=owning_team.id,
                deleted=False,
                document_directory_id=None,
                created_at=payload.created_at,
                updated_at=payload.updated_at,
            )
            await cruds_documents.create_template(template=template, db=db)

        case WebhookEvent.TEMPLATE_UPDATED:
            payload = webhook.payload
            await cruds_documents.update_template_name_by_documenso_id(
                db=db,
                documenso_id=str(payload.id),
                name=payload.title,
            )

        case WebhookEvent.TEMPLATE_DELETED:
            payload = webhook.payload
            await cruds_documents.mark_template_deleted(
                db=db,
                documenso_id=str(payload.id),
            )

        case WebhookEvent.DOCUMENT_COMPLETED:
            payload = webhook.payload
            if not payload.recipients:
                return
            signing_token = payload.recipients[0].token

            await cruds_documents.update_document_status_by_signing_token(
                db=db,
                signing_token=signing_token,
                status=DocumentStatus.COMPLETED,
            )

        case WebhookEvent.DOCUMENT_REJECTED:
            payload = webhook.payload
            if not payload.recipients:
                return
            signing_token = payload.recipients[0].token

            await cruds_documents.update_document_status_by_signing_token(
                db=db,
                signing_token=signing_token,
                status=DocumentStatus.REJECTED,
            )
