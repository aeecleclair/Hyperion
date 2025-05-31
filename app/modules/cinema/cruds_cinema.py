from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cinema import models_cinema, schemas_cinema


async def get_sessions(db: AsyncSession) -> Sequence[models_cinema.Session]:
    result = await db.execute(select(models_cinema.Session))
    return result.scalars().all()


async def get_sessions_in_time_frame(
    start_after: datetime,
    start_before: datetime,
    db: AsyncSession,
) -> Sequence[models_cinema.Session]:
    result = await db.execute(
        select(models_cinema.Session)
        .where(
            models_cinema.Session.start >= start_after,
            models_cinema.Session.start < start_before,
        )
        .order_by(models_cinema.Session.start),
    )
    return result.scalars().all()


async def get_session_by_id(
    db: AsyncSession,
    session_id: str,
) -> models_cinema.Session | None:
    result = await db.execute(
        select(models_cinema.Session).where(models_cinema.Session.id == session_id),
    )
    return result.scalars().first()


async def create_session(
    session: schemas_cinema.CineSessionComplete,
    db: AsyncSession,
) -> models_cinema.Session:
    db_session = models_cinema.Session(**session.model_dump())
    db.add(db_session)
    await db.flush()
    return db_session


async def update_session(
    session_id: str,
    session_update: schemas_cinema.CineSessionUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_cinema.Session)
        .where(models_cinema.Session.id == session_id)
        .values(**session_update.model_dump(exclude_none=True)),
    )
    await db.flush()


async def delete_session(session_id: str, db: AsyncSession):
    await db.execute(
        delete(models_cinema.Session).where(models_cinema.Session.id == session_id),
    )
    await db.flush()
