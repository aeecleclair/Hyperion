import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.cmm import models_cmm, schemas_cmm, types_cmm

n_memes = 10
n_weeks = 7


async def compute_schemas(meme_page, votes_map) -> Sequence[schemas_cmm.FullMeme]:
    full_meme_page = [schemas_cmm.FullMeme(**meme.model_dump()) for meme in meme_page]
    for i, meme in enumerate(meme_page):
        if meme.id in votes_map:
            full_meme_page[i].my_vote = meme.positive
    return full_meme_page


async def get_memes_by_date(
    db: AsyncSession,
    n_page: int,
    descending: bool,
    user_id: str,
) -> Sequence[schemas_cmm.FullMeme]:
    result = await db.execute(
        select(models_cmm.Meme)
        .where(models_cmm.Meme.status == types_cmm.MemeStatus.neutral)
        .order_by(
            models_cmm.Meme.creation_time.desc()
            if descending
            else models_cmm.Meme.creation_time,
        )
        .fetch(n_memes)
        .offset((n_page - 1) * n_memes),
    )
    votes_map = await get_my_votes_from_memes(
        db=db,
        user_id=user_id,
        meme_result=result,
    )
    return await compute_schemas(result.scalars().all(), votes_map)


async def get_memes_by_votes(
    db: AsyncSession,
    n_page: int,
    descending: bool,
    user_id: str,
) -> Sequence[schemas_cmm.FullMeme]:
    result = await db.execute(
        select(models_cmm.Meme)
        .where(models_cmm.Meme.status == types_cmm.MemeStatus.neutral)
        .order_by(
            models_cmm.Meme.vote_score.desc()
            if descending
            else models_cmm.Meme.vote_score,
        )
        .fetch(n_memes)
        .offset((n_page - 1) * n_memes),
    )
    votes_map = await get_my_votes_from_memes(
        db=db,
        user_id=user_id,
        meme_result=result,
    )
    return await compute_schemas(result.scalars().all(), votes_map)


async def get_trending_memes(
    db: AsyncSession,
    n_page: int,
    user_id: str,
) -> Sequence[schemas_cmm.FullMeme]:
    result = await db.execute(
        select(models_cmm.Meme)
        .order_by(models_cmm.Meme.vote_score)
        .where(
            (models_cmm.Meme.creation_time - datetime.now(tz=UTC))
            < timedelta(days=n_weeks),
            models_cmm.Meme.status == types_cmm.MemeStatus.neutral,
        )
        .fetch(n_memes)
        .offset((n_page - 1) * n_memes),
    )
    votes_map = await get_my_votes_from_memes(
        db=db,
        user_id=user_id,
        meme_result=result,
    )
    return await compute_schemas(result.scalars().all(), votes_map)


async def get_memes_from_user(
    db: AsyncSession,
    user_id: str,
) -> Sequence[schemas_cmm.FullMeme]:
    result = await db.execute(
        select(models_cmm.Meme)
        .where(
            models_cmm.Meme.user_id == user_id,
            models_cmm.Meme.status == types_cmm.MemeStatus.neutral,
        )
        .order_by(models_cmm.Meme.creation_time),
    )
    votes_map = await get_my_votes_from_memes(
        db=db,
        user_id=user_id,
        meme_result=result,
    )
    return await compute_schemas(result.scalars().all(), votes_map)


async def update_ban_status_of_memes_from_user(
    db: AsyncSession,
    user_id: str,
    new_ban_status: types_cmm.MemeStatus,
):
    await db.execute(
        update(models_cmm.Meme)
        .where(models_cmm.Meme.user_id == user_id)
        .values({models_cmm.Meme.status: new_ban_status}),
    )


async def get_meme_by_id(
    db: AsyncSession,
    meme_id: uuid.UUID,
) -> models_cmm.Meme | None:
    result = await db.execute(
        select(models_cmm.Meme)
        .options(selectinload(models_cmm.Meme.votes))
        .where(models_cmm.Meme.id == meme_id),
    )
    return result.unique().scalars().first()


async def get_my_votes_from_memes(
    db: AsyncSession,
    user_id: str,
    meme_result,
) -> dict[UUID, models_cmm.Vote]:
    result = await db.execute(
        select(models_cmm.Vote)
        .join(meme_result, meme_result.id == models_cmm.Vote.meme_id)
        .where(
            models_cmm.Vote.user_id == user_id,
        ),
    )
    votes = result.scalars().all()
    votes_map = {vote.meme_id: vote for vote in votes}
    return votes_map


def add_meme(db: AsyncSession, meme: models_cmm.Meme):
    db.add(meme)


async def update_meme_ban_status(
    db: AsyncSession,
    ban_status: types_cmm.MemeStatus,
    meme_id: UUID,
):
    await db.execute(
        update(models_cmm.Meme)
        .where(models_cmm.Meme.id == meme_id)
        .values({models_cmm.Meme.status: ban_status}),
    )


async def delete_meme_by_id(db: AsyncSession, meme_id: UUID):
    await db.execute(
        delete(models_cmm.Meme).where(models_cmm.Meme.id == meme_id),
    )


async def get_vote(
    db: AsyncSession,
    meme_id: UUID,
    user_id: str,
) -> models_cmm.Vote | None:
    result = await db.execute(
        select(models_cmm.Vote).where(
            models_cmm.Vote.meme_id == meme_id,
            models_cmm.Vote.user_id == user_id,
        ),
    )
    return result.unique().scalars().first()


async def get_vote_by_id(
    db: AsyncSession,
    vote_id: UUID,
) -> models_cmm.Vote | None:
    result = await db.execute(
        select(models_cmm.Vote).where(models_cmm.Vote.id == vote_id),
    )
    return result.unique().scalars().first()


def add_vote(db: AsyncSession, vote: models_cmm.Vote):
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


async def get_ban_by_id(
    db: AsyncSession,
    ban_id: UUID,
) -> models_cmm.Ban | None:
    result = await db.execute(
        select(models_cmm.Ban).where(models_cmm.Ban.id == ban_id),
    )
    return result.unique().scalars().first()


async def get_user_current_ban(
    db: AsyncSession,
    user_id: str,
) -> models_cmm.Ban | None:
    result = await db.execute(
        select(models_cmm.Ban).where(
            models_cmm.Ban.user_id == user_id,
            models_cmm.Ban.end_time.is_(None),
        ),
    )
    return result.unique().scalars().first()


async def get_user_ban_history(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_cmm.Ban]:
    result = await db.execute(
        select(models_cmm.Ban)
        .where(models_cmm.Ban.user_id == user_id)
        .order_by(models_cmm.Ban.creation_time),
    )
    return result.scalars().all()


def add_user_ban(db: AsyncSession, ban: models_cmm.Ban):
    db.add(ban)


async def update_end_of_ban(db: AsyncSession, end_time: datetime, ban_id: UUID):
    await db.execute(
        update(models_cmm.Ban)
        .where(models_cmm.Ban.id == ban_id)
        .values({models_cmm.Ban.end_time: end_time}),
    )


async def delete_ban(db: AsyncSession, ban_id: UUID):
    await db.execute(
        delete(models_cmm.Ban).where(models_cmm.Ban.id == ban_id),
    )
