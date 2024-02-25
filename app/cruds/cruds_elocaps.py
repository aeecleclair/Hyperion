from datetime import date
from typing import Sequence

from sqlalchemy import desc, func, not_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_elocaps
from app.schemas import schemas_elocaps
from app.utils.types.elocaps_types import CapsMode


async def get_latest_games(db: AsyncSession, count=10) -> Sequence[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .order_by(desc(models_elocaps.Game.timestamp))
        .options(
            selectinload(models_elocaps.Game.game_players)
            .selectinload(models_elocaps.GamePlayer.player)
            .selectinload(models_elocaps.Player.user)
        )
        .limit(count)
    )
    return result.scalars().all()


async def get_games_played_on(
    db: AsyncSession, time: date
) -> Sequence[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .where(func.DATE(models_elocaps.Game.timestamp) == time)
        .options(
            selectinload(models_elocaps.Game.game_players)
            .selectinload(models_elocaps.GamePlayer.player)
            .selectinload(models_elocaps.Player.user)
        )
    )
    return result.scalars().all()


async def get_player_info(
    db: AsyncSession, user_id: str
) -> Sequence[models_elocaps.Player]:
    result = await db.execute(
        select(models_elocaps.Player)
        .where(models_elocaps.Player.user_id == user_id)
        .options(selectinload(models_elocaps.Player.user))
    )
    return result.scalars().all()


async def get_player_games(db: AsyncSession, user_id: str) -> list[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.GamePlayer)
        .join(models_elocaps.Player)
        .where(models_elocaps.Player.user_id == user_id)
        .options(
            selectinload(models_elocaps.GamePlayer.game)
            .selectinload(models_elocaps.Game.game_players)
            .selectinload(models_elocaps.GamePlayer.player)
            .selectinload(models_elocaps.Player.user)
        )
    )
    return [i.game for i in result.scalars().all()]


async def get_game_details(
    db: AsyncSession, game_id: str
) -> models_elocaps.Game | None:
    result = await db.execute(
        select(models_elocaps.Game)
        .where(models_elocaps.Game.id == game_id)
        .options(
            selectinload(models_elocaps.Game.game_players)
            .selectinload(models_elocaps.GamePlayer.player)
            .selectinload(models_elocaps.Player.user)
        )
    )
    return result.scalars().first()


async def create_game(db: AsyncSession, game: models_elocaps.Game) -> None:
    db.add(game)
    await db.commit()


async def insert_player_into_game(
    db: AsyncSession,
    game: models_elocaps.Game,
    player_info: schemas_elocaps.GamePlayerBase,
) -> None:
    try:
        player = (
            (
                await db.execute(
                    select(models_elocaps.Player).where(
                        (models_elocaps.Player.user_id == player_info.user_id)
                        & (models_elocaps.Player.mode == game.mode)
                    )
                )
            )
            .scalars()
            .first()
        )
        if not player:
            player = models_elocaps.Player(user_id=player_info.user_id, mode=game.mode)
            db.add(player)
            await db.commit()
        game_player = models_elocaps.GamePlayer(
            game_id=game.id,
            player_id=player.id,
            team=player_info.team,
            score=player_info.score,
        )
        db.add(game_player)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def set_player_elo_gain(
    db: AsyncSession, game_player: models_elocaps.GamePlayer, gain: int
) -> None:
    game_player.elo_gain = gain
    await db.commit()


async def get_waiting_games(
    db: AsyncSession, user_id: str
) -> Sequence[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .join(models_elocaps.GamePlayer)
        .join(models_elocaps.Player)
        .where(
            (models_elocaps.Player.user_id == user_id)
            & not_(models_elocaps.GamePlayer.has_confirmed)
            & not_(models_elocaps.Game.is_cancelled)
        )
    )
    return result.scalars().all()


async def get_game_player(
    db: AsyncSession, game_id: str, user_id: str
) -> models_elocaps.GamePlayer | None:
    return (
        (
            await db.execute(
                select(models_elocaps.GamePlayer)
                .join(models_elocaps.Player)
                .where(
                    (models_elocaps.Player.user_id == user_id)
                    & (models_elocaps.GamePlayer.game_id == game_id)
                )
                .options(
                    selectinload(models_elocaps.GamePlayer.game).selectinload(
                        models_elocaps.Game.game_players
                    )
                )
            )
        )
        .scalars()
        .first()
    )


async def user_game_validation(
    db: AsyncSession, game_player: models_elocaps.GamePlayer
) -> None:
    game_player.has_confirmed = True
    await db.commit()


async def end_game(db: AsyncSession, game_id: str) -> None:
    game: models_elocaps.Game | None = (
        (
            await db.execute(
                select(models_elocaps.Game)
                .where(models_elocaps.Game.id == game_id)
                .options(
                    selectinload(models_elocaps.Game.game_players).selectinload(
                        models_elocaps.GamePlayer.player
                    )
                )
            )
        )
        .scalars()
        .first()
    )
    if game is None:
        raise ValueError("This game does not exist")
    for x in game.game_players:
        x.player.elo += x.elo_gain
    await db.commit()


async def get_leaderboard(
    db: AsyncSession, game_mode: CapsMode, count=10
) -> Sequence[models_elocaps.Player]:
    result = await db.execute(
        select(models_elocaps.Player)
        .where(models_elocaps.Player.mode == game_mode)
        .order_by(desc(models_elocaps.Player.elo))
        .limit(count)
        .options(selectinload(models_elocaps.Player.user))
    )
    return result.scalars().all()


async def get_winrate(
    db: AsyncSession,
    game_mode: CapsMode,
    user_id: str,
) -> float | None:
    result = await db.execute(
        (
            select(models_elocaps.Game)
            .join(models_elocaps.GamePlayer)
            .join(models_elocaps.Player)
            .where(
                (models_elocaps.Game.mode == game_mode)
                & (models_elocaps.Player.user_id == user_id)
            )
            .options(
                selectinload(models_elocaps.Game.game_players).selectinload(
                    models_elocaps.GamePlayer.player
                )
            )
        )
    )
    games: list[models_elocaps.Game] = [
        x for x in result.scalars().all() if x.is_confirmed
    ]
    if len(games) == 0:
        return None
    return round(
        sum(1 for x in games if x.get_winner_team() == x.get_user_team(user_id))
        / len(games),
        2,
    )


async def cancel_game(db: AsyncSession, game: models_elocaps.Game) -> None:
    game.is_cancelled = True
    await db.commit()
