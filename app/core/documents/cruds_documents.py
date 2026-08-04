from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import ScalarSelect, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.core.documents import models_documents, schemas_documents
from app.core.documents.types_documenso import DocumentStatus
from app.core.documents.utils_documents import (
    document_model_to_schema,
    document_with_team_info_model_to_schema,
    document_with_user_model_to_schema,
    team_complete_model_to_schema,
    team_model_to_schema,
    template_complete_with_documents_model_to_schema,
    template_with_statistics_model_to_schema,
)


def _template_statistics_subqueries() -> tuple[
    ScalarSelect[int],
    ScalarSelect[int],
    ScalarSelect[int],
    ScalarSelect[int],
]:
    def base(*extra):
        return (
            select(func.count(models_documents.DocumentDocument.id))
            .where(
                models_documents.DocumentDocument.template_id
                == models_documents.DocumentTemplate.id,
                *extra,
            )
            .correlate(models_documents.DocumentTemplate)
            .scalar_subquery()
        )

    return (
        base(),
        base(models_documents.DocumentDocument.status == DocumentStatus.COMPLETED),
        base(models_documents.DocumentDocument.status == DocumentStatus.PENDING),
        base(models_documents.DocumentDocument.status == DocumentStatus.REJECTED),
    )


# region Team


async def get_teams(db: AsyncSession) -> list[schemas_documents.Team]:
    """Return all teams from database."""

    result = await db.execute(select(models_documents.DocumentTeam))
    return [team_model_to_schema(team) for team in result.scalars().all()]


async def get_team_by_id(
    db: AsyncSession,
    team_id: UUID,
) -> schemas_documents.Team | None:
    """Return a team by its internal id."""

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


async def get_teams_by_group_ids(
    db: AsyncSession,
    group_ids: list[str],
) -> list[schemas_documents.TeamComplete]:
    """Return teams by their group ids, along with their templates and statistics."""

    teams = (
        (
            await db.execute(
                select(models_documents.DocumentTeam)
                .where(
                    models_documents.DocumentTeam.group_id.in_(group_ids),
                )
                .options(
                    selectinload(models_documents.DocumentTeam.group),
                    noload(models_documents.DocumentTeam.templates),
                ),
            )
        )
        .scalars()
        .all()
    )

    if not teams:
        return []

    team_ids = [team.id for team in teams]

    total_sq, completed_sq, pending_sq, rejected_sq = _template_statistics_subqueries()

    templates_result = await db.execute(
        select(
            models_documents.DocumentTemplate,
            total_sq.label("total_documents"),
            completed_sq.label("total_signed_documents"),
            pending_sq.label("total_pending_documents"),
            rejected_sq.label("total_rejected_documents"),
        )
        .where(
            models_documents.DocumentTemplate.team_id.in_(team_ids),
        )
        .options(
            noload(models_documents.DocumentTemplate.documents),
        ),
    )

    templates_by_team_id: dict[UUID, list[schemas_documents.TemplateWithStatistics]] = (
        defaultdict(list)
    )
    for (
        template,
        total_documents,
        total_signed_documents,
        total_pending_documents,
        total_rejected_documents,
    ) in templates_result.all():
        templates_by_team_id[template.team_id].append(
            template_with_statistics_model_to_schema(
                template,
                schemas_documents.TemplateStatistics(
                    total_documents=total_documents,
                    total_signed_documents=total_signed_documents,
                    total_pending_documents=total_pending_documents,
                    total_rejected_documents=total_rejected_documents,
                ),
            ),
        )

    return [
        team_complete_model_to_schema(team, templates_by_team_id.get(team.id, []))
        for team in teams
    ]


async def get_team_by_name(
    db: AsyncSession,
    name: str,
) -> schemas_documents.Team | None:
    """Return a team by its name."""

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


async def get_team_by_team_id(
    db: AsyncSession,
    team_id: int,
) -> schemas_documents.Team | None:
    """Return a team by its Documenso team id."""

    result = (
        (
            await db.execute(
                select(models_documents.DocumentTeam).where(
                    models_documents.DocumentTeam.team_id == team_id,
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
    """Return a team by its linked group id."""

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
    """Create a new team in database."""

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
    """Update an existing team."""

    await db.execute(
        update(models_documents.DocumentTeam)
        .where(models_documents.DocumentTeam.id == team_id)
        .values(**team_update.model_dump(exclude_unset=True)),
    )


async def delete_team(db: AsyncSession, team_id: UUID) -> None:
    """Delete a team from database by id."""

    await db.execute(
        delete(models_documents.DocumentTeam).where(
            models_documents.DocumentTeam.id == team_id,
        ),
    )


# endregion Team
# region Template


async def get_team_templates_with_statistics(
    db: AsyncSession,
    team_id: UUID,
) -> list[schemas_documents.TemplateWithStatistics]:
    """Return all templates filtered by team, with document statistics."""

    total_sq, completed_sq, pending_sq, rejected_sq = _template_statistics_subqueries()

    result = await db.execute(
        select(
            models_documents.DocumentTemplate,
            total_sq.label("total_documents"),
            completed_sq.label("total_signed_documents"),
            pending_sq.label("total_pending_documents"),
            rejected_sq.label("total_rejected_documents"),
        )
        .where(
            models_documents.DocumentTemplate.team_id == team_id,
        )
        .options(
            noload(models_documents.DocumentTemplate.documents),
        ),
    )
    return [
        template_with_statistics_model_to_schema(
            template,
            schemas_documents.TemplateStatistics(
                total_documents=total_documents,
                total_signed_documents=total_signed_documents,
                total_pending_documents=total_pending_documents,
                total_rejected_documents=total_rejected_documents,
            ),
        )
        for (
            template,
            total_documents,
            total_signed_documents,
            total_pending_documents,
            total_rejected_documents,
        ) in result.all()
    ]


async def get_template_by_id(
    db: AsyncSession,
    template_id: UUID,
) -> schemas_documents.TemplateCompleteWithDocuments | None:
    """Return a template by its internal id."""

    result = (
        (
            await db.execute(
                select(models_documents.DocumentTemplate)
                .where(
                    models_documents.DocumentTemplate.id == template_id,
                )
                .options(
                    selectinload(models_documents.DocumentTemplate.documents),
                ),
            )
        )
        .scalars()
        .first()
    )
    return template_complete_with_documents_model_to_schema(result) if result else None


async def get_template_by_documenso_id(
    db: AsyncSession,
    documenso_id: int,
) -> schemas_documents.TemplateCompleteWithDocuments | None:
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
    return template_complete_with_documents_model_to_schema(result) if result else None


async def create_template(
    template: schemas_documents.Template,
    db: AsyncSession,
) -> None:
    """Create a new template in database."""

    db.add(
        models_documents.DocumentTemplate(
            id=template.id,
            documenso_id=template.documenso_id,
            name=template.name,
            recipient_id=template.recipient_id,
            team_id=template.team_id,
            generate_email=template.generate_email,
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
    """Update a template"""

    await db.execute(
        update(models_documents.DocumentTemplate)
        .where(models_documents.DocumentTemplate.id == template_id)
        .values(
            **template_update.model_dump(exclude_unset=True),
            updated_at=datetime.now(UTC),
        ),
    )


# endregion Template
# region Document


async def get_documents_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> list[schemas_documents.DocumentWithTeamInfo]:
    """Return all documents assigned to a user (without signing token)"""

    result = await db.execute(
        select(models_documents.DocumentDocument)
        .where(
            models_documents.DocumentDocument.user_id == user_id,
        )
        .options(
            selectinload(models_documents.DocumentDocument.template).selectinload(
                models_documents.DocumentTemplate.team,
            ),
        ),
    )
    return [
        document_with_team_info_model_to_schema(doc) for doc in result.scalars().all()
    ]


async def get_documents_by_template_id(
    db: AsyncSession,
    template_id: UUID,
) -> list[schemas_documents.DocumentWithUser]:
    """Return all documents generated from a given template"""

    result = await db.execute(
        select(models_documents.DocumentDocument).where(
            models_documents.DocumentDocument.template_id == template_id,
        ),
    )
    return [document_with_user_model_to_schema(doc) for doc in result.scalars().all()]


async def get_document_by_id(
    db: AsyncSession,
    document_id: UUID,
) -> schemas_documents.Document | None:
    """Return a single document with all fields"""

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
    return document_model_to_schema(result) if result else None


async def get_document_with_token_by_id(
    db: AsyncSession,
    document_id: UUID,
) -> schemas_documents.DocumentWithToken | None:
    """Return a single document with signing token only"""

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
    """Update document status"""

    await db.execute(
        update(models_documents.DocumentDocument)
        .where(models_documents.DocumentDocument.id == document_id)
        .values(status=status, updated_at=datetime.now(UTC)),
    )


async def delete_document_by_id(
    db: AsyncSession,
    document_id: UUID,
) -> None:
    """Delete a document from database by id"""

    await db.execute(
        delete(models_documents.DocumentDocument).where(
            models_documents.DocumentDocument.id == document_id,
        ),
    )


# endregion Document
