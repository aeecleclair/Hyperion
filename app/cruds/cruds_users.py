"""File defining the functions called by the endpoints, making queries to the table using the models"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import models_core
from ..schemas import schemas_core
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload


async def get_users(db: AsyncSession) -> list[models_core.CoreUser]:
    """Return all users from database as a list of dictionaries"""

    result = await db.execute(select(models_core.CoreUser))
    return result.scalars().all()


async def get_user_by_id(db: AsyncSession, user_id: int) -> models_core.CoreUser:
    """Return user with id from database as a dictionary"""

    result = await db.execute(
        select(models_core.CoreUser)
        .where(models_core.CoreUser.id == user_id)
        .options(
            selectinload(models_core.CoreUser.groups)
        )  # needed to load the members from the relationship
    )
    return result.scalars().first()


async def create_user(
    user: schemas_core.CoreUserCreate, db: AsyncSession
) -> models_core.CoreUser:
    """Create a new user in database and return it as a dictionary"""

    fakePassword = user.password + "notreallyhashed"
    db_user = models_core.CoreUser(
        password=fakePassword,
        name=user.name,
        firstname=user.firstname,
        nickname=user.nickname,
        birthday=user.birthday,
        promo=user.promo,
        floor=user.floor,
        email=user.email,
        created_on=user.created_on,
    )
    db.add(db_user)
    try:
        await db.commit()
        return db_user
    except IntegrityError:
        await db.rollback()
        raise ValueError("Email already registered")


async def delete_user(db: AsyncSession, user_id: int):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUser).where(models_core.CoreUser.id == user_id)
    )
    await db.commit()
