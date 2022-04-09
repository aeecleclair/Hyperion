"""File defining the functions called by the endpoints, making queries to the table using the models"""

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.security import get_password_hash
import secrets

from app.utils.types.account_type import AccountType

from app.models import models_core
from app.schemas import schemas_core


async def get_users(db: AsyncSession) -> list[models_core.CoreUser]:
    """Return all users from database"""

    result = await db.execute(select(models_core.CoreUser))
    return result.scalars().all()


async def get_user_by_id(db: AsyncSession, user_id: int) -> models_core.CoreUser:
    """Return user with id"""

    result = await db.execute(
        select(models_core.CoreUser)
        .where(models_core.CoreUser.id == user_id)
        .options(
            # The group relationship need to be loaded
            selectinload(models_core.CoreUser.groups)
        )
    )
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> models_core.CoreUser:
    """Return user with id from database as a dictionary"""

    result = await db.execute(
        select(models_core.CoreUser)
        .where(models_core.CoreUser.email == email)
        .options(
            # The group relationship need to be loaded
            selectinload(models_core.CoreUser.groups)
        )
    )
    return result.scalars().first()


"""
async def create_user(
    user: schemas_core.CoreUserCreate, db: AsyncSession
) -> models_core.CoreUser:
    """Create a new user in database and return it"""
    \"""Create a new user in database and return it as a dictionar\"""

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
"""


async def create_unconfirmed_user(
    db: AsyncSession, user: schemas_core.CoreUserCreate
) -> models_core.CoreUserUnconfirmed:
    """
    Create a new user in the unconfirmed database

    On utilise un https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe pour le token
    """

    db_user_unconfirmed = models_core.CoreUserUnconfirmed(
        id=str(uuid.uuid4()),  # Use UUID later
        email=user.email,
        password_hash=get_password_hash(user.password),
        activation_token=secrets.token_urlsafe(32),
        created_on=datetime.datetime.now(),
        expire_on=datetime.datetime.now() + datetime.timedelta(days=1),
        account_type=user.account_type,
    )
    db.add(db_user_unconfirmed)
    try:
        await db.commit()
        return db_user_unconfirmed
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_unconfirmed_user_by_activation_token(
    db: AsyncSession, activation_token: str
) -> models_core.CoreUserUnconfirmed:

    result = await db.execute(
        select(models_core.CoreUserUnconfirmed).where(
            models_core.CoreUserUnconfirmed.activation_token == activation_token
        )
    )
    return result.scalars().first()


async def delete_unconfirmed_user_by_email(db: AsyncSession, email: str):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUserUnconfirmed).where(
            models_core.CoreUserUnconfirmed.email == email
        )
    )
    await db.commit()


async def create_user(
    db: AsyncSession, user: schemas_core.CoreUserInDB
) -> models_core.CoreUser:

    db_user = models_core.CoreUser(
        id=user.id,
        email=user.email,
        password_hash=user.password_hash,
        name=user.name,
        firstname=user.firstname,
        nickname=user.nickname,
        birthday=user.birthday,
        promo=user.promo,
        phone=user.phone,
        floor=user.floor,
        created_on=user.created_on,
        account_type=user.account_type,
    )

    db.add(db_user)
    try:
        await db.commit()
        return db_user
    except:
        await db.rollback()
        raise


async def delete_user(db: AsyncSession, user_id: int):
    """Delete a user from database by id"""

    await db.execute(
        delete(models_core.CoreUser).where(models_core.CoreUser.id == user_id)
    )
    await db.commit()
