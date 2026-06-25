import logging
import uuid
from datetime import UTC, datetime

from documenso_sdk import TemplateCreateDocumentFromTemplateRecipientRequest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.documents import cruds_documents, models_documents, schemas_documents
from app.core.documents.documenso_tool import DocumensoTool
from app.core.documents.types_documenso import DocumentStatus, TemplateCreatedPayload
from app.core.groups.schemas_groups import CoreGroup
from app.core.users import cruds_users
from app.core.users.schemas_users import CoreUser
from app.module import all_modules

hyperion_error_logger = logging.getLogger("hyperion.error")


def template_model_to_schema(
    model: models_documents.DocumentTemplate,
) -> schemas_documents.Template:
    """Convert a DocumentTemplate model to a Template schema."""
    return schemas_documents.Template(
        id=model.id,
        documenso_id=model.documenso_id,
        name=model.name,
        team_id=model.team_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted=model.deleted,
        document_directory_id=model.document_directory_id,
    )


def team_model_to_schema(
    model: models_documents.DocumentTeam,
) -> schemas_documents.Team:
    """Convert a DocumentTeam model to a Team schema."""
    return schemas_documents.Team(
        id=model.id,
        team_id=model.team_id,
        api_key=model.api_key,
        name=model.name,
        group_id=model.group_id,
    )


def template_complete_model_to_schema(
    model: models_documents.DocumentTemplate,
) -> schemas_documents.TemplateComplete:
    """Convert a DocumentTemplate model to a TemplateComplete schema."""
    return schemas_documents.TemplateComplete(
        id=model.id,
        documenso_id=model.documenso_id,
        name=model.name,
        team_id=model.team_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted=model.deleted,
        document_directory_id=model.document_directory_id,
        documents=[document_model_to_schema(document) for document in model.documents],
        team=team_model_to_schema(model.team),
    )


def team_complete_model_to_schema(
    model: models_documents.DocumentTeam,
) -> schemas_documents.TeamComplete:
    """Convert a DocumentTeam model to a TeamComplete schema."""
    return schemas_documents.TeamComplete(
        id=model.id,
        team_id=model.team_id,
        api_key=model.api_key,
        name=model.name,
        group_id=model.group_id,
        templates=[template_model_to_schema(template) for template in model.templates],
        group=CoreGroup(
            id=model.group.id,
            name=model.group.name,
            description=model.group.description,
        ),
    )


def document_model_to_schema(
    model: models_documents.DocumentDocument,
) -> schemas_documents.Document:
    """Convert a DocumentDocument model to a Document schema."""
    return schemas_documents.Document(
        id=model.id,
        name=model.name,
        template_id=model.template_id,
        module=model.module,
        user_id=model.user_id,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def document_complete_model_to_schema(
    model: models_documents.DocumentDocument,
) -> schemas_documents.DocumentComplete:
    """Convert a DocumentDocument model to a DocumentComplete schema."""
    return schemas_documents.DocumentComplete(
        id=model.id,
        name=model.name,
        template_id=model.template_id,
        module=model.module,
        user_id=model.user_id,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
        user=CoreUser(
            id=model.user.id,
            name=model.user.name,
            firstname=model.user.firstname,
            email=model.user.email,
            account_type=model.user.account_type,
            school_id=model.user.school_id,
        ),
    )


async def handle_template_creation_webhook(
    payload: TemplateCreatedPayload,
    db: AsyncSession,
) -> None:
    if payload.team_id is None:
        return
    if len(payload.recipients) != 1:
        return  # MyECL only handle templates with a single recipient

    all_teams = await cruds_documents.get_teams(db=db)
    owning_team = next(
        (t for t in all_teams if str(t.team_id) == str(payload.team_id)),
        None,
    )
    if owning_team is None:
        return

    template = schemas_documents.Template(
        id=uuid.uuid4(),
        documenso_id=payload.id,
        name=payload.title,
        team_id=owning_team.id,
        deleted=False,
        document_directory_id=None,
        created_at=payload.created_at,
        updated_at=payload.updated_at,
    )
    await cruds_documents.create_template(template=template, db=db)


async def use_template_for_a_recipient(
    recipient_email: str,
    template: schemas_documents.Template,
    destination_folder_id: str,
    documenso: DocumensoTool,
    db: AsyncSession,
    module: str,
    errors: dict[str, str],
) -> schemas_documents.Document | None:
    target_user = await cruds_users.get_user_by_email(
        db=db,
        email=recipient_email,
    )
    if target_user is None:
        errors[recipient_email] = "User not found"
        return None
    document_id = uuid.uuid4()
    documenso_response = await documenso.use_template(
        template_id=float(template.documenso_id),
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
        errors[recipient_email] = "No recipients found in Documenso response"
        return None

    signing_token = documenso_response.recipients[0].token

    document = schemas_documents.DocumentWithToken(
        id=document_id,
        template_id=template.id,
        name=documenso_response.title,
        module=module,
        user_id=target_user.id,
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


async def handle_document_callback(
    document_module: str,
    document_id: uuid.UUID,
    status: DocumentStatus,
    db: AsyncSession,
) -> None:
    try:
        for module in all_modules:
            if module.root == document_module:
                if module.document_callback is not None:
                    hyperion_error_logger.info(
                        f"Documents: calling module {document_module} document callback",
                    )
                    await module.document_callback(document_id, status, db)
                    hyperion_error_logger.info(
                        f"Documents: call to module {document_module} document callback for document (document_id: {document_id}, status: {status}) succeeded",
                    )
                    return
    except Exception:
        hyperion_error_logger.exception(
            f"Documents: call to module {document_module} document callback for document (document_id: {document_id}, status: {status}) failed",
        )
