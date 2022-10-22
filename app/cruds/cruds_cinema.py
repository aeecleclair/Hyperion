from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_cinema
from app.schemas import schemas_cinema


async def get_sessions(db: AsyncSession) -> list[models_cinema.Session]:
    result = await db.execute(select(models_cinema.Session))
    return result.scalars().all()


async def create_session(
    session: schemas_cinema.CineSessionComplete, db: AsyncSession
) -> models_cinema.Session:
    db_session = models_cinema.Session(**session.dict())
    db.add(db_session)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
    return db_session


async def update_session(
    session_id: str, session_update: schemas_cinema.CineSessionUpdate, db: AsyncSession
):
    await db.execute(
        update(models_cinema.Session)
        .where(models_cinema.Session.id == session_id)
        .values(**session_update.dict(exclude_none=True))
    )
    await db.commit()


async def delete_session(session_id: str, db: AsyncSession):
    await db.execute(
        delete(models_cinema.Session).where(models_cinema.Session.id == session_id)
    )
    await db.commit()
