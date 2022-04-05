from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import models_core
from ..schemas import schemas_core
from sqlalchemy import select, delete


async def get_users(db: AsyncSession) -> list[models_core.CoreUser]:
    result = await db.execute(select(models_core.CoreUser))
    return result.scalars().all()


async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(models_core.CoreUser).where(models_core.CoreUser.id == user_id)
    )
    return result.scalars().first()


async def create_user(user: schemas_core.CoreUserCreate, db: AsyncSession):
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
    await db.execute(
        delete(models_core.CoreUser).where(models_core.CoreUser.id == user_id)
    )
    await db.commit()


# def get_user_by_email(db: AsyncSession, email: str):
#     return db.query(models_users.User).filter(models_users.User.email == email).first()
