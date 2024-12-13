from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.modules.cmm import models_cmm, types_cmm

n_memes = 10
n_weeks = 7


async def get_memes_by_date(
    db: AsyncSession,
    n_page: int,
    descending: bool,
) -> Sequence[models_cmm.Meme]:
    result = await db.execute(
        select(models_cmm.Meme)
        .order_by(
            models_cmm.Meme.creation_time.desc()
            if descending
            else models_cmm.Meme.creation_time,
        )
        .fetch(n_memes)
        .offset((n_page - 1) * n_memes),
    )
    return result.scalars().all()


async def get_memes_by_votes(
    db: AsyncSession,
    n_page: int,
    descending: bool,
) -> Sequence[models_cmm.Meme]:
    result = await db.execute(
        select(models_cmm.Meme)
        .order_by(
            models_cmm.Meme.vote_score.desc()
            if descending
            else models_cmm.Meme.vote_score,
        )
        .fetch(n_memes)
        .offset((n_page - 1) * n_memes),
    )
    return result.scalars().all()


async def get_trending_memes(
    db: AsyncSession,
    n_page: int,
) -> Sequence[models_cmm.Meme]:
    result = await db.execute(
        select(models_cmm.Meme)
        .order_by(models_cmm.Meme.vote_score)
        .where(
            (models_cmm.Meme.creation_time - datetime.now(tz=UTC))
            < timedelta(days=n_weeks),
        )
        .fetch(n_memes)
        .offset((n_page - 1) * n_memes),
    )
    return result.scalars().all()


async def get_memes_from_user(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_cmm.Meme]:
    result = await db.execute(
        select(models_cmm.Meme)
        .where(models_cmm.Meme.user_id == user_id)
        .order_by(models_cmm.Meme.creation_time),
    )
    return result.scalars().all()


async def get_reported_memes(db: AsyncSession) -> Sequence[models_cmm.Meme]:
    result = await db.execute(
        select(models_cmm.Meme).where(
            models_cmm.Meme.status == types_cmm.MemeStatus.reported,
        ),
    )
    return result.scalars().all()


async def create_meme(db: AsyncSession, meme: models_cmm.Meme):
    db.add(meme)


async def delete_meme(db: AsyncSession, meme_id: UUID):
    await db.execute(
        delete(models_cmm.Meme).where(models_cmm.Meme.id == meme_id),
    )


async def create_report(db: AsyncSession, report: models_cmm.Report):
    db.add(report)


async def delete_report(db: AsyncSession, report_id: UUID):
    await db.execute(
        delete(models_cmm.Report).where(models_cmm.Meme.id == report_id),
    )


async def create_vote(db: AsyncSession, vote: models_cmm.Vote):
    db.add(vote)


async def update_vote(db: AsyncSession, vote_id: UUID, new_positive: bool):
    await db.execute(
        update(models_cmm.Vote)
        .where(models_cmm.Vote.id == vote_id)
        .values({models_cmm.Vote.positive: new_positive}),
    )


async def delete_vote(db: AsyncSession, vote_id: UUID):
    await db.execute(
        delete(models_cmm.Vote).where(models_cmm.Vote.id == vote_id),
    )
