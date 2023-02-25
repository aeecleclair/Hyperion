from datetime import date

from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_elocaps
from app.utils.types.elocaps_types import CapsMode


async def get_latest_games(db: AsyncSession, count=10) -> list[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .order_by(desc(models_elocaps.Game.timestamp))
        .limit(count)
    )
    return result.scalars().all()


async def get_games_played_on(
    db: AsyncSession, time: date
) -> list[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .order_by(desc(models_elocaps.Game.timestamp))
        .where(models_elocaps.Game.timestamp.date() == time)
    )
    return result.scalars().all()


async def get_player_info(
    db: AsyncSession, user_id: str
) -> list[models_elocaps.Player]:
    result = await db.execute(
        select(models_elocaps.Player).where(models_elocaps.Player.user_id == user_id)
    )
    return result.scalars().all()


async def get_player_games(db: AsyncSession, user_id: str) -> list[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.GamePlayer)
        .where(models_elocaps.GamePlayer.user_id == user_id)
        .options(selectinload(models_elocaps.GamePlayer.game))
    )
    return [i.game for i in result.scalars().all()]


async def get_game_details(
    db: AsyncSession, game_id: str
) -> models_elocaps.Game | None:
    result = await db.execute(
        select(models_elocaps.Game)
        .where(models_elocaps.Game.id == game_id)
        .options(selectinload(models_elocaps.Game.players))
    )
    return result.scalars().first()


async def register_game(db: AsyncSession, game: models_elocaps.Game) -> None:
    db.add(game)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def register_game_players(
    db: AsyncSession, game_players: list[models_elocaps.GamePlayer]
) -> list[models_elocaps.GamePlayer]:
    db.add_all(game_players)
    try:
        await db.commit()
        return game_players
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_leaderboard(
    db: AsyncSession, game_mode: CapsMode, count=10
) -> list[models_elocaps.Player]:
    result = await db.execute(
        select(models_elocaps.Player)
        .where(models_elocaps.Player.mode == game_mode)
        .order_by(desc(models_elocaps.Player.elo))
        .limit(count)
    )
    return result.scalars().all()
