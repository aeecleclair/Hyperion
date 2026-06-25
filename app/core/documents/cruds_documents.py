from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.documents import models_documents, schemas_documents
from app.core.documents.types_documenso import DocumentStatus
from app.core.documents.utils_documents import (
    document_complete_model_to_schema,
    document_model_to_schema,
    team_complete_model_to_schema,
    team_model_to_schema,
    template_complete_model_to_schema,
    template_model_to_schema,
)

# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------


async def get_teams(db: AsyncSession) -> list[schemas_documents.Team]:
    """Return all document teams from database."""

    result = await db.execute(select(models_documents.DocumentTeam))
    return [team_model_to_schema(team) for team in result.scalars().all()]


async def get_team_by_id(
    db: AsyncSession,
    team_id: UUID,
) -> schemas_documents.Team | None:
    """Return a document team by its internal id."""

    result = (
        (
            await db.execute(
                select(models_documents.DocumentTeam).where(
                    models_documents.DocumentTeam.id == team_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return team_model_to_schema(result) if result else None


async def get_team_by_group_ids(
    db: AsyncSession,
    group_ids: list[str],
) -> list[schemas_documents.TeamComplete]:
    """Return a document team by its internal id."""

    result = (
        (
            await db.execute(
                select(models_documents.DocumentTeam)
                .where(
                    models_documents.DocumentTeam.group_id.in_(group_ids),
                )
                .options(
                    selectinload(models_documents.DocumentTeam.templates),
                    selectinload(models_documents.DocumentTeam.group),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [team_complete_model_to_schema(team) for team in result]


async def get_team_by_name(
    db: AsyncSession,
    name: str,
) -> schemas_documents.Team | None:
    """Return a document team by its name."""

    result = (
        (
            await db.execute(
                select(models_documents.DocumentTeam).where(
                    models_documents.DocumentTeam.name == name,
                ),
            )
        )
        .scalars()
        .first()
    )
    return team_model_to_schema(result) if result else None


async def get_team_by_group_id(
    db: AsyncSession,
    group_id: str,
) -> schemas_documents.Team | None:
    """Return a document team by its linked MyECL group id."""

    result = (
        (
            await db.execute(
                select(models_documents.DocumentTeam).where(
                    models_documents.DocumentTeam.group_id == group_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return team_model_to_schema(result) if result else None


async def create_team(
    team: schemas_documents.Team,
    db: AsyncSession,
) -> None:
    """Create a new document team in database."""

    db.add(
        models_documents.DocumentTeam(
            id=team.id,
            team_id=team.team_id,
            group_id=team.group_id,
            name=team.name,
            api_key=team.api_key,
        ),
    )


async def update_team(
    db: AsyncSession,
    team_id: UUID,
    team_update: schemas_documents.TeamUpdate,
) -> None:
    """Update an existing document team."""

    await db.execute(
        update(models_documents.DocumentTeam)
        .where(models_documents.DocumentTeam.id == team_id)
        .values(**team_update.model_dump(exclude_none=True)),
    )


async def delete_team(db: AsyncSession, team_id: UUID) -> None:
    """Delete a document team from database by id."""

    await db.execute(
        delete(models_documents.DocumentTeam).where(
            models_documents.DocumentTeam.id == team_id,
        ),
    )


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------


async def get_team_templates(
    db: AsyncSession,
    team_id: UUID,
) -> list[schemas_documents.Template]:
    """Return all templates, optionally filtered by team."""

    result = await db.execute(
        select(models_documents.DocumentTemplate).where(
            models_documents.DocumentTemplate.team_id == team_id,
        ),
    )
    return [template_model_to_schema(template) for template in result.scalars().all()]


async def get_template_by_id(
    db: AsyncSession,
    template_id: UUID,
) -> schemas_documents.TemplateComplete | None:
    """Return a template by its internal id."""

    result = (
        (
            await db.execute(
                select(models_documents.DocumentTemplate).where(
                    models_documents.DocumentTemplate.id == template_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return template_complete_model_to_schema(result) if result else None


async def get_template_by_documenso_id(
    db: AsyncSession,
    documenso_id: int,
) -> schemas_documents.TemplateComplete | None:
    """Return a template by its Documenso id."""

    result = (
        (
            await db.execute(
                select(models_documents.DocumentTemplate).where(
                    models_documents.DocumentTemplate.documenso_id == documenso_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return template_complete_model_to_schema(result) if result else None


async def create_template(
    template: schemas_documents.Template,
    db: AsyncSession,
) -> None:
    """Create a new document template in database."""

    db.add(
        models_documents.DocumentTemplate(
            id=template.id,
            documenso_id=template.documenso_id,
            name=template.name,
            team_id=template.team_id,
            deleted=template.deleted,
            document_directory_id=template.document_directory_id,
            created_at=template.created_at,
            updated_at=template.updated_at,
        ),
    )


async def update_template(
    db: AsyncSession,
    template_id: UUID,
    template_update: schemas_documents.TemplateUpdate
    | schemas_documents.TemplateDocumensoUpdate,
) -> None:
    """Update a document template (directory only, from the public API)."""

    await db.execute(
        update(models_documents.DocumentTemplate)
        .where(models_documents.DocumentTemplate.id == template_id)
        .values(
            **template_update.model_dump(exclude_unset=True),
            updated_at=datetime.now(UTC),
        ),
    )


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


async def get_documents_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> list[schemas_documents.Document]:
    """Return all documents assigned to a user (without signing token)."""

    result = await db.execute(
        select(models_documents.DocumentDocument).where(
            models_documents.DocumentDocument.user_id == user_id,
        ),
    )
    return [document_model_to_schema(doc) for doc in result.scalars().all()]


async def get_documents_by_template_id(
    db: AsyncSession,
    template_id: UUID,
) -> list[schemas_documents.DocumentComplete]:
    """Return all documents generated from a given template (admin view)."""

    result = await db.execute(
        select(models_documents.DocumentDocument).where(
            models_documents.DocumentDocument.template_id == template_id,
        ),
    )
    return [document_complete_model_to_schema(doc) for doc in result.scalars().all()]


async def get_document_by_id(
    db: AsyncSession,
    document_id: UUID,
) -> schemas_documents.DocumentComplete | None:
    """Return a single document with all fields (including signing token)."""

    result = (
        (
            await db.execute(
                select(models_documents.DocumentDocument).where(
                    models_documents.DocumentDocument.id == document_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return document_complete_model_to_schema(result) if result else None


async def get_document_with_token_by_id(
    db: AsyncSession,
    document_id: UUID,
) -> schemas_documents.DocumentWithToken | None:
    """Return a single document with signing token only (for user view)."""

    result = (
        (
            await db.execute(
                select(models_documents.DocumentDocument).where(
                    models_documents.DocumentDocument.id == document_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_documents.DocumentWithToken(
            id=result.id,
            documenso_id=result.documenso_id,
            name=result.name,
            template_id=result.template_id,
            module=result.module,
            user_id=result.user_id,
            signing_token=result.signing_token,
            status=result.status,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
        if result
        else None
    )


async def create_document(
    document: schemas_documents.DocumentWithToken,
    db: AsyncSession,
) -> None:
    """Persist a newly generated document."""

    db.add(
        models_documents.DocumentDocument(
            id=document.id,
            documenso_id=document.documenso_id,
            name=document.name,
            template_id=document.template_id,
            module=document.module,
            user_id=document.user_id,
            signing_token=document.signing_token,
            status=document.status,
            created_at=document.created_at,
            updated_at=document.updated_at,
        ),
    )


async def update_document(
    db: AsyncSession,
    document_id: UUID,
    status: DocumentStatus,
) -> None:
    """Update document status identified by its signing token (called from webhook)."""

    await db.execute(
        update(models_documents.DocumentDocument)
        .where(models_documents.DocumentDocument.id == document_id)
        .values(status=status, updated_at=datetime.now(UTC)),
    )


async def delete_document_by_id(
    db: AsyncSession,
    document_id: UUID,
) -> None:
    """Delete a document from database by id."""

    await db.execute(
        delete(models_documents.DocumentDocument).where(
            models_documents.DocumentDocument.id == document_id,
        ),
    )
