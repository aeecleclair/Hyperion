import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import models_core
from app.modules.meme import models_meme, types_meme

n_weeks = 7


async def get_memes_by_date(
    db: AsyncSession,
    descending: bool,
    user_id: str,
) -> Sequence[models_meme.Meme]:
    result = await db.execute(
        select(models_meme.Meme)
        .options(
            selectinload(
                models_meme.Meme.votes.and_(models_meme.Vote.user_id == user_id),
            ).load_only(models_meme.Vote.positive),
            selectinload(models_meme.Meme.user),
        )
        .execution_options(populate_existing=True)
        .where(models_meme.Meme.status == types_meme.MemeStatus.neutral)
        .order_by(
            models_meme.Meme.creation_time.desc()
            if descending
            else models_meme.Meme.creation_time,
        ),
    )
    meme_page = result.scalars().all()
    return meme_page


async def get_my_memes(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_meme.Meme]:
    result = await db.execute(
        select(models_meme.Meme)
        .options(
            selectinload(
                models_meme.Meme.votes.and_(models_meme.Vote.user_id == user_id),
            ).load_only(models_meme.Vote.positive),
            selectinload(models_meme.Meme.user),
        )
        .execution_options(populate_existing=True)
        .where(models_meme.Meme.user_id == user_id)
        .order_by(models_meme.Meme.creation_time.desc())
    )
    meme_page = result.scalars().all()
    return meme_page


async def get_memes_by_votes(
    db: AsyncSession,
    descending: bool,
    user_id: str,
) -> Sequence[models_meme.Meme]:
    result = await db.execute(
        select(models_meme.Meme)
        .where(models_meme.Meme.status == types_meme.MemeStatus.neutral)
        .options(
            selectinload(
                models_meme.Meme.votes.and_(models_meme.Vote.user_id == user_id),
            ).load_only(models_meme.Vote.positive),
            selectinload(models_meme.Meme.user),
        )
        .execution_options(populate_existing=True)
        .order_by(
            models_meme.Meme.vote_score.desc()
            if descending
            else models_meme.Meme.vote_score,
        ),
    )
    meme_page = result.scalars().all()
    return meme_page


async def get_trending_memes(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_meme.Meme]:
    result = await db.execute(
        select(models_meme.Meme)
        .order_by(models_meme.Meme.vote_score)
        .options(
            selectinload(
                models_meme.Meme.votes.and_(models_meme.Vote.user_id == user_id),
            ).load_only(models_meme.Vote.positive),
            selectinload(models_meme.Meme.user),
        )
        .execution_options(populate_existing=True)
        .where(
            (models_meme.Meme.creation_time - datetime.now(tz=UTC))
            < timedelta(days=n_weeks),
            models_meme.Meme.status == types_meme.MemeStatus.neutral,
        ),
    )
    meme_page = result.scalars().all()
    return meme_page


async def get_memes_from_user(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_meme.Meme]:
    result = await db.execute(
        select(models_meme.Meme)
        .options(
            selectinload(
                models_meme.Meme.votes.and_(models_meme.Vote.user_id == user_id),
            ).load_only(models_meme.Vote.positive),
            selectinload(models_meme.Meme.user),
        )
        .execution_options(populate_existing=True)
        .where(
            models_meme.Meme.user_id == user_id,
            models_meme.Meme.status == types_meme.MemeStatus.neutral,
        )
        .order_by(models_meme.Meme.creation_time),
    )
    meme_page = result.scalars().all()
    return meme_page


async def update_ban_status_of_memes_from_user(
    db: AsyncSession,
    user_id: str,
    new_ban_status: types_meme.MemeStatus,
):
    await db.execute(
        update(models_meme.Meme)
        .where(models_meme.Meme.user_id == user_id)
        .values({models_meme.Meme.status: new_ban_status}),
    )


async def get_meme_by_id(
    db: AsyncSession,
    meme_id: uuid.UUID,
    user_id: str,
) -> models_meme.Meme | None:
    result = await db.execute(
        select(models_meme.Meme)
        .options(
            selectinload(
                models_meme.Meme.votes.and_(
                    models_meme.Vote.user_id == user_id,
                ),
            ).load_only(models_meme.Vote.positive),
            selectinload(models_meme.Meme.user),
        )
        .execution_options(populate_existing=True)
        .where(models_meme.Meme.id == meme_id),
    )
    return result.unique().scalars().first()


def add_meme(db: AsyncSession, meme: models_meme.Meme):
    db.add(meme)


async def update_meme_ban_status(
    db: AsyncSession,
    ban_status: types_meme.MemeStatus,
    meme_id: UUID,
):
    await db.execute(
        update(models_meme.Meme)
        .where(models_meme.Meme.id == meme_id)
        .values({models_meme.Meme.status: ban_status}),
    )


async def update_meme_vote_score(
    db: AsyncSession,
    old_positive: bool | None,
    new_positive: bool | None,
    meme_id: UUID,
):
    if old_positive == new_positive:
        score_diff = 0
    elif old_positive is None:
        score_diff = 1 if new_positive else -1
    elif not old_positive:
        score_diff = 1 if new_positive is None else 2
    else:
        # old_positve == True
        score_diff = -1 if new_positive is None else -2

    await db.execute(
        update(models_meme.Meme)
        .where(models_meme.Meme.id == meme_id)
        .values(
            {models_meme.Meme.vote_score: models_meme.Meme.vote_score + score_diff},
        ),
    )


async def delete_meme_by_id(db: AsyncSession, meme_id: UUID):
    await db.execute(
        delete(models_meme.Meme).where(models_meme.Meme.id == meme_id),
    )


async def get_vote(
    db: AsyncSession,
    meme_id: UUID,
    user_id: str,
) -> models_meme.Vote | None:
    result = await db.execute(
        select(models_meme.Vote).where(
            models_meme.Vote.meme_id == meme_id,
            models_meme.Vote.user_id == user_id,
        ),
    )
    return result.unique().scalars().first()


async def get_vote_by_id(
    db: AsyncSession,
    vote_id: UUID,
) -> models_meme.Vote | None:
    result = await db.execute(
        select(models_meme.Vote).where(models_meme.Vote.id == vote_id),
    )
    return result.unique().scalars().first()


def add_vote(db: AsyncSession, vote: models_meme.Vote):
    db.add(vote)


async def update_vote(db: AsyncSession, vote_id: UUID, new_positive: bool):
    await db.execute(
        update(models_meme.Vote)
        .where(models_meme.Vote.id == vote_id)
        .values({models_meme.Vote.positive: new_positive}),
    )


async def delete_vote(db: AsyncSession, vote_id: UUID):
    await db.execute(
        delete(models_meme.Vote).where(models_meme.Vote.id == vote_id),
    )


async def get_ban_by_id(
    db: AsyncSession,
    ban_id: UUID,
) -> models_meme.Ban | None:
    result = await db.execute(
        select(models_meme.Ban).where(models_meme.Ban.id == ban_id),
    )
    return result.unique().scalars().first()


async def get_user_current_ban(
    db: AsyncSession,
    user_id: str,
) -> models_meme.Ban | None:
    result = await db.execute(
        select(models_meme.Ban).where(
            models_meme.Ban.user_id == user_id,
            models_meme.Ban.end_time.is_(None),
        ),
    )
    return result.unique().scalars().first()


async def get_user_ban_history(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_meme.Ban]:
    result = await db.execute(
        select(models_meme.Ban)
        .where(models_meme.Ban.user_id == user_id)
        .order_by(models_meme.Ban.creation_time),
    )
    return result.scalars().all()


def add_user_ban(db: AsyncSession, ban: models_meme.Ban):
    db.add(ban)


async def update_end_of_ban(db: AsyncSession, end_time: datetime, ban_id: UUID):
    await db.execute(
        update(models_meme.Ban)
        .where(models_meme.Ban.id == ban_id)
        .values({models_meme.Ban.end_time: end_time}),
    )


async def delete_ban(db: AsyncSession, ban_id: UUID):
    await db.execute(
        delete(models_meme.Ban).where(models_meme.Ban.id == ban_id),
    )


async def get_banned_users(db: AsyncSession) -> Sequence[models_core.CoreUser]:
    result = await db.execute(
        select(models_core.CoreUser)
        .join(models_meme.Ban, models_core.CoreUser.id == models_meme.Ban.user_id)
        .where(models_meme.Ban.end_time.is_(None))
        .order_by(models_meme.Ban.creation_time),
    )
    return result.scalars().all()


async def get_hidden_memes(
    db: AsyncSession,
    descending: bool,
    user_id: str,
) -> Sequence[models_meme.Meme]:
    result = await db.execute(
        select(models_meme.Meme)
        .options(
            selectinload(
                models_meme.Meme.votes.and_(models_meme.Vote.user_id == user_id),
            ).load_only(models_meme.Vote.positive),
            selectinload(models_meme.Meme.user),
        )
        .execution_options(populate_existing=True)
        .where(models_meme.Meme.status == types_meme.MemeStatus.banned)
        .order_by(
            models_meme.Meme.creation_time.desc()
            if descending
            else models_meme.Meme.creation_time,
        ),
    )
    return result.scalars().all()


async def get_all_memes(db: AsyncSession, n_jours) -> Sequence[models_meme.Meme]:
    if n_jours == -1:
        result = await db.execute(
            select(models_meme.Meme)
            .where(
                models_meme.Meme.status == types_meme.MemeStatus.neutral,
            )
            .options(selectinload(models_meme.Meme.user)),
        )

    else:
        threshold_date = datetime.now(tz=UTC) - timedelta(days=n_jours)

        result = await db.execute(
            select(models_meme.Meme)
            .where(
                models_meme.Meme.creation_time >= threshold_date,
                models_meme.Meme.status == types_meme.MemeStatus.neutral,
            )
            .options(selectinload(models_meme.Meme.user)),
        )
    return result.scalars().all()
