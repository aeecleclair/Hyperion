from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.groups import schemas_groups
from app.modules.identity import models_identity, schemas_identity


async def create_verification_context(
    verification_context: schemas_identity.VerificationContext,
    db: AsyncSession,
) -> None:
    db.add(
        models_identity.VerificationContext(
            id=verification_context.id,
            name=verification_context.name,
            archived=verification_context.archived,
            group_id=verification_context.group_id,
        ),
    )


async def get_verification_contexts_by_group_ids(
    group_ids: list[str],
    db: AsyncSession,
) -> Sequence[schemas_identity.VerificationContextComplete]:
    result = await db.execute(
        select(models_identity.VerificationContext)
        .where(models_identity.VerificationContext.group_id.in_(group_ids))
        .options(selectinload(models_identity.VerificationContext.group)),
    )
    return [
        schemas_identity.VerificationContextComplete(
            id=context.id,
            name=context.name,
            group_id=context.group_id,
            archived=context.archived,
            group=schemas_groups.CoreGroupSimple(
                id=context.group.id,
                name=context.group.name,
            ),
        )
        for context in result.scalars().all()
    ]


async def get_verification_context_by_id(
    context_id: UUID,
    db: AsyncSession,
) -> schemas_identity.VerificationContext | None:
    result = await db.execute(
        select(models_identity.VerificationContext).where(
            models_identity.VerificationContext.id == context_id,
        ),
    )
    context = result.scalars().first()
    return (
        schemas_identity.VerificationContext(
            id=context.id,
            name=context.name,
            group_id=context.group_id,
            archived=context.archived,
        )
        if context is not None
        else None
    )


async def update_verification_context_edit(
    context_id: UUID,
    context_edit: schemas_identity.VerificationContextEdit,
    db: AsyncSession,
) -> None:
    await db.execute(
        update(models_identity.VerificationContext)
        .where(models_identity.VerificationContext.id == context_id)
        .values(**context_edit.model_dump(exclude_unset=True)),
    )


async def get_identity_information_by_token(
    token: str,
    db: AsyncSession,
) -> schemas_identity.IdentityTokenResponse | None:
    result = await db.execute(
        select(models_identity.IdentityToken)
        .where(models_identity.IdentityToken.token == token)
        .options(selectinload(models_identity.IdentityToken.user)),
    )
    identity_token = result.scalars().first()

    return (
        schemas_identity.IdentityTokenResponse(
            id=identity_token.id,
            token=identity_token.token,
            expire_on=identity_token.expire_on,
            name=identity_token.user.name,
            firstname=identity_token.user.firstname,
            nickname=identity_token.user.nickname,
            user_id=identity_token.user_id,
        )
        if identity_token is not None
        else None
    )


async def create_verification_scan(
    scan: schemas_identity.VerificationScan,
    db: AsyncSession,
) -> None:
    db.add(
        models_identity.VerificationScan(
            id=scan.id,
            user_id=scan.user_id,
            verification_context_id=scan.verification_context_id,
            datetime=scan.datetime,
            scanner_user_id=scan.scanner_user_id,
        ),
    )


async def get_verification_scans_by_context_id(
    context_id: UUID,
    db: AsyncSession,
) -> Sequence[schemas_identity.VerificationScanComplete]:
    result = await db.execute(
        select(models_identity.VerificationScan)
        .where(models_identity.VerificationScan.verification_context_id == context_id)
        .options(selectinload(models_identity.VerificationScan.user)),
    )
    return [
        schemas_identity.VerificationScanComplete(
            id=scan.id,
            user_id=scan.user_id,
            verification_context_id=scan.verification_context_id,
            datetime=scan.datetime,
            scanner_user_id=scan.scanner_user_id,
            user=scan.user,
        )
        for scan in result.scalars().all()
    ]


async def get_verification_scans_by_context_id_and_user_id(
    context_id: UUID,
    user_id: str,
    db: AsyncSession,
) -> Sequence[schemas_identity.VerificationScan]:
    result = await db.execute(
        select(models_identity.VerificationScan)
        .where(
            models_identity.VerificationScan.verification_context_id == context_id,
            models_identity.VerificationScan.user_id == user_id,
        )
        .options(selectinload(models_identity.VerificationScan.user)),
    )
    scans = result.scalars().all()
    return [
        schemas_identity.VerificationScan(
            id=scan.id,
            user_id=scan.user_id,
            verification_context_id=scan.verification_context_id,
            datetime=scan.datetime,
            scanner_user_id=scan.scanner_user_id,
        )
        for scan in scans
    ]


async def create_identity_token(
    identity_token: schemas_identity.IdentityToken,
    db: AsyncSession,
) -> None:
    db.add(
        models_identity.IdentityToken(
            id=identity_token.id,
            token=identity_token.token,
            user_id=identity_token.user_id,
            expire_on=identity_token.expire_on,
        ),
    )
