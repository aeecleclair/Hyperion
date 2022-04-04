from sqlalchemy.ext.asyncio import AsyncSession
from ..models import models_users
from ..schemas import schemas_users
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload


async def get_users(db: AsyncSession) -> list[models_users.CoreUser]:
    result = await db.execute(
        select(models_users.CoreUser).options(
            selectinload(models_users.CoreUser.groups)
        )
    )
    return result.scalars().all()


async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(models_users.CoreUser).where(models_users.CoreUser.id == user_id)
    )
    return result.scalars().first()


def create_user(user: schemas_users.CoreUserCreate, db: AsyncSession):
    fakePassword = user.password + "notreallyhashed"
    db_user = models_users.CoreUser(
        login=user.login,
        password=fakePassword,
        name=user.name,
        firstname=user.firstname,
        nick=user.nick,
        birth=user.birth,
        promo=user.promo,
        floor=user.floor,
        created_on=user.created_on,
        email=user.email,
    )
    db.add(db_user)
    print(db_user.id)
    return db_user


async def get_groups(db: AsyncSession):
    result = await db.execute(
        select(models_users.CoreGroup).options(
            selectinload(models_users.CoreGroup.members)
        )
    )
    return result.scalars().all()


async def delete_user(db: AsyncSession, user_id: int):
    await db.execute(
        delete(models_users.CoreUser).where(models_users.CoreUser.id == user_id)
    )
    await db.commit()


# def get_user_by_email(db: AsyncSession, email: str):
#     return db.query(models_users.User).filter(models_users.User.email == email).first()
