from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.documents import models_documents, schemas_documents
from app.core.documents.types_documenso import DocumentStatus

# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------


async def get_teams(db: AsyncSession) -> list[schemas_documents.Team]:
    """Return all document teams from database."""

    result = await db.execute(select(models_documents.DocumentTeam))
    return [
        schemas_documents.Team(
            id=team.id,
            team_id=team.team_id,
            group_id=team.group_id,
            name=team.name,
            api_key=team.api_key,
            documenso_url=team.documenso_url,
        )
        for team in result.scalars().all()
    ]


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
    return (
        schemas_documents.Team(
            id=result.id,
            team_id=result.team_id,
            group_id=result.group_id,
            name=result.name,
            api_key=result.api_key,
            documenso_url=result.documenso_url,
        )
        if result
        else None
    )


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
    return (
        schemas_documents.Team(
            id=result.id,
            team_id=result.team_id,
            group_id=result.group_id,
            name=result.name,
            api_key=result.api_key,
            documenso_url=result.documenso_url,
        )
        if result
        else None
    )


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
    return (
        schemas_documents.Team(
            id=result.id,
            team_id=result.team_id,
            group_id=result.group_id,
            name=result.name,
            api_key=result.api_key,
            documenso_url=result.documenso_url,
        )
        if result
        else None
    )


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
            documenso_url=team.documenso_url,
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


async def get_templates(
    db: AsyncSession,
    team_id: UUID | None = None,
) -> list[schemas_documents.Template]:
    """Return all templates, optionally filtered by team."""

    query = select(models_documents.DocumentTemplate).where(
        models_documents.DocumentTemplate.deleted == False,  # noqa: E712
    )
    if team_id is not None:
        query = query.where(models_documents.DocumentTemplate.team_id == team_id)

    result = await db.execute(query)
    return [
        schemas_documents.Template(
            id=template.id,
            documenso_id=template.documenso_id,
            name=template.name,
            team_id=template.team_id,
            deleted=template.deleted,
            document_directory_id=template.document_directory_id,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
        for template in result.scalars().all()
    ]


async def get_template_by_id(
    db: AsyncSession,
    template_id: UUID,
) -> schemas_documents.Template | None:
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
    return (
        schemas_documents.Template(
            id=result.id,
            documenso_id=result.documenso_id,
            name=result.name,
            team_id=result.team_id,
            deleted=result.deleted,
            document_directory_id=result.document_directory_id,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
        if result
        else None
    )


async def get_template_by_documenso_id(
    db: AsyncSession,
    documenso_id: str,
) -> schemas_documents.Template | None:
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
    return (
        schemas_documents.Template(
            id=result.id,
            documenso_id=result.documenso_id,
            name=result.name,
            team_id=result.team_id,
            deleted=result.deleted,
            document_directory_id=result.document_directory_id,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
        if result
        else None
    )


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
    template_update: schemas_documents.TemplateUpdate,
) -> None:
    """Update a document template (directory only, from the public API)."""

    await db.execute(
        update(models_documents.DocumentTemplate)
        .where(models_documents.DocumentTemplate.id == template_id)
        .values(**template_update.model_dump(exclude_none=True)),
    )


async def mark_template_deleted(
    db: AsyncSession,
    documenso_id: str,
) -> None:
    """Soft-delete a template identified by its Documenso id."""

    await db.execute(
        update(models_documents.DocumentTemplate)
        .where(models_documents.DocumentTemplate.documenso_id == documenso_id)
        .values(deleted=True, updated_at=datetime.now(UTC)),
    )


async def update_template_name_by_documenso_id(
    db: AsyncSession,
    documenso_id: str,
    name: str,
) -> None:
    """Update a template name when Documenso reports an update."""

    await db.execute(
        update(models_documents.DocumentTemplate)
        .where(models_documents.DocumentTemplate.documenso_id == documenso_id)
        .values(name=name, updated_at=datetime.now(UTC)),
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
    return [
        schemas_documents.Document(
            id=doc.id,
            template_id=doc.template_id,
            name=doc.name,
            user_id=doc.user_id,
            module=doc.module,
            status=doc.status,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        for doc in result.scalars().all()
    ]


async def get_documents_by_template_id(
    db: AsyncSession,
    template_id: UUID,
) -> list[schemas_documents.Document]:
    """Return all documents generated from a given template (admin view)."""

    result = await db.execute(
        select(models_documents.DocumentDocument).where(
            models_documents.DocumentDocument.template_id == template_id,
        ),
    )
    return [
        schemas_documents.Document(
            id=doc.id,
            template_id=doc.template_id,
            name=doc.name,
            user_id=doc.user_id,
            module=doc.module,
            status=doc.status,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        for doc in result.scalars().all()
    ]


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
    return (
        schemas_documents.DocumentComplete(
            id=result.id,
            template_id=result.template_id,
            name=result.name,
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
    document: schemas_documents.DocumentComplete,
    db: AsyncSession,
) -> None:
    """Persist a newly generated document."""

    db.add(
        models_documents.DocumentDocument(
            id=document.id,
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


async def update_document_status_by_signing_token(
    db: AsyncSession,
    signing_token: str,
    status: DocumentStatus,
) -> None:
    """Update document status identified by its signing token (called from webhook)."""

    await db.execute(
        update(models_documents.DocumentDocument)
        .where(models_documents.DocumentDocument.signing_token == signing_token)
        .values(status=status, updated_at=datetime.now(UTC)),
    )
