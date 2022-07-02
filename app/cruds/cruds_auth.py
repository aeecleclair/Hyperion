"""File defining the functions called by the endpoints, making queries to the table using the models"""

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_auth


async def get_authorization_token_by_token(
    db: AsyncSession, code: str
) -> models_auth.AuthorizationCode | None:
    """Return group with id from database"""
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
