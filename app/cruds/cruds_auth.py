"""File defining the functions called by the endpoints, making queries to the table using the models"""

from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_auth


async def get_authorization_token_by_token(
    db: AsyncSession, code: str
) -> models_auth.AuthorizationCode | None:
    """Return authorization code from database"""
    result = await db.execute(
        select(models_auth.AuthorizationCode).where(
            models_auth.AuthorizationCode.code == code
        )
    )
    return result.scalars().first()


async def create_authorization_token(
    db_authorization_code: models_auth.AuthorizationCode, db: AsyncSession
) -> models_auth.AuthorizationCode:
    """Create a new group in database and return it"""

    db.add(db_authorization_code)
    try:
        await db.commit()
        return db_authorization_code
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def delete_authorization_token_by_token(
    db: AsyncSession, code: str
) -> models_auth.AuthorizationCode | None:
    """Delete a token from database"""

    await db.execute(
        delete(models_auth.AuthorizationCode).where(
            models_auth.AuthorizationCode.code == code
        )
    )
    await db.commit()
    return None


async def get_refresh_token_by_token(
    db: AsyncSession, token: str
) -> models_auth.RefreshToken | None:
    """Return refresh token from database"""
    result = await db.execute(
        select(models_auth.RefreshToken).where(models_auth.RefreshToken.token == token)
    )
    return result.scalars().first()


async def create_refresh_token(
    db_refresh_token: models_auth.RefreshToken, db: AsyncSession
) -> models_auth.RefreshToken:
    """Create a new refresh token in database and return it"""

    db.add(db_refresh_token)
    try:
        await db.commit()
        return db_refresh_token
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def revoke_refresh_token_by_token(
    db: AsyncSession, token: str
) -> models_auth.RefreshToken | None:
    """Revoke a refresh token from database"""

    await db.execute(
        update(models_auth.RefreshToken)
        .where(
            models_auth.RefreshToken.token == token,
            models_auth.RefreshToken.revoked_on.is_(None),
        )
        .values(revoked_on=datetime.now())
    )
    await db.commit()
    return None


async def revoke_refresh_token_by_client_id(
    db: AsyncSession, client_id: str
) -> models_auth.RefreshToken | None:
    """Revoke a refresh token from database"""

    await db.execute(
        update(models_auth.RefreshToken)
        .where(
            models_auth.RefreshToken.client_id == client_id,
            models_auth.RefreshToken.revoked_on.is_(None),
        )
        .values(revoked_on=datetime.now())
    )
    await db.commit()
    return None
