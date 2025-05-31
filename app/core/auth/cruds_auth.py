"""File defining the functions called by the endpoints, making queries to the table using the models"""

from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import models_auth


async def get_authorization_token_by_token(
    db: AsyncSession,
    code: str,
) -> models_auth.AuthorizationCode | None:
    """Return authorization code from database"""
    result = await db.execute(
        select(models_auth.AuthorizationCode).where(
            models_auth.AuthorizationCode.code == code,
        ),
    )
    return result.scalars().first()


async def create_authorization_token(
    db_authorization_code: models_auth.AuthorizationCode,
    db: AsyncSession,
) -> models_auth.AuthorizationCode:
    """Create a new group in database and return it"""

    db.add(db_authorization_code)
    await db.flush()
    return db_authorization_code


async def delete_authorization_token_by_token(
    db: AsyncSession,
    code: str,
) -> models_auth.AuthorizationCode | None:
    """Delete a token from database"""

    await db.execute(
        delete(models_auth.AuthorizationCode).where(
            models_auth.AuthorizationCode.code == code,
        ),
    )
    await db.flush()
    return None


async def get_refresh_token_by_token(
    db: AsyncSession,
    token: str,
) -> models_auth.RefreshToken | None:
    """Return refresh token from database"""
    result = await db.execute(
        select(models_auth.RefreshToken).where(models_auth.RefreshToken.token == token),
    )
    return result.scalars().first()


async def create_refresh_token(
    db_refresh_token: models_auth.RefreshToken,
    db: AsyncSession,
) -> models_auth.RefreshToken:
    """Create a new refresh token in database and return it"""

    db.add(db_refresh_token)
    await db.flush()
    return db_refresh_token


async def revoke_refresh_token_by_token(
    db: AsyncSession,
    token: str,
) -> models_auth.RefreshToken | None:
    """Revoke a refresh token from database"""

    await db.execute(
        update(models_auth.RefreshToken)
        .where(
            models_auth.RefreshToken.token == token,
            models_auth.RefreshToken.revoked_on.is_(None),
        )
        .values(revoked_on=datetime.now(UTC)),
    )
    await db.flush()
    return None


async def revoke_refresh_token_by_client_and_user_id(
    db: AsyncSession,
    client_id: str,
    user_id: str,
) -> None:
    """Revoke a refresh token from database"""

    await db.execute(
        update(models_auth.RefreshToken)
        .where(
            models_auth.RefreshToken.client_id == client_id,
            models_auth.RefreshToken.user_id == user_id,
            models_auth.RefreshToken.revoked_on.is_(None),
        )
        .values(revoked_on=datetime.now(UTC)),
    )
    await db.flush()


async def revoke_refresh_token_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> None:
    """Revoke a refresh token from database"""

    await db.execute(
        update(models_auth.RefreshToken)
        .where(
            models_auth.RefreshToken.user_id == user_id,
            models_auth.RefreshToken.revoked_on.is_(None),
        )
        .values(revoked_on=datetime.now(UTC)),
    )
    await db.flush()
