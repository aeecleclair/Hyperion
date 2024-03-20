from collections.abc import Sequence
from datetime import date

from sqlalchemy import desc, func, not_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.elocaps import models_elocaps
from app.modules.elocaps.types_elocaps import CapsMode


async def get_latest_games(db: AsyncSession, count=10) -> Sequence[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .order_by(desc(models_elocaps.Game.timestamp))
        .options(
            selectinload(models_elocaps.Game.game_players)
            .selectinload(models_elocaps.GamePlayer.player)
            .selectinload(models_elocaps.Player.user),
        )
        .limit(count),
    )
    return result.scalars().all()


async def get_games_played_on(
    db: AsyncSession,
    time: date,
) -> Sequence[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .where(func.DATE(models_elocaps.Game.timestamp) == time)
        .options(
            selectinload(models_elocaps.Game.game_players)
            .selectinload(models_elocaps.GamePlayer.player)
            .selectinload(models_elocaps.Player.user),
        ),
    )
    return result.scalars().all()


async def get_player_info(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_elocaps.Player]:
    """Return a list of Player objects corresponding to the different caps modes the user has played in."""
    result = await db.execute(
        select(models_elocaps.Player)
        .where(models_elocaps.Player.user_id == user_id)
        .options(selectinload(models_elocaps.Player.user)),
    )
    return result.scalars().all()


async def get_player_games(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .join(models_elocaps.GamePlayer)
        .join(models_elocaps.Player)
        .where(models_elocaps.Player.user_id == user_id)
        .options(
            selectinload(models_elocaps.Game.game_players)
            .selectinload(models_elocaps.GamePlayer.player)
            .selectinload(models_elocaps.Player.user),
        ),
    )
    return result.scalars().all()


async def get_game_details(
    db: AsyncSession,
    game_id: str,
) -> models_elocaps.Game | None:
    result = await db.execute(
        select(models_elocaps.Game)
        .where(models_elocaps.Game.id == game_id)
        .options(
            selectinload(models_elocaps.Game.game_players)
            .selectinload(models_elocaps.GamePlayer.player)
            .selectinload(models_elocaps.Player.user),
        ),
    )
    return result.scalars().first()


async def create_game(db: AsyncSession, game: models_elocaps.Game) -> None:
    db.add(game)
    await db.commit()


async def get_player(
    db: AsyncSession,
    user_id: str,
    mode: CapsMode,
) -> models_elocaps.Player | None:
    player = (
        (
            await db.execute(
                select(models_elocaps.Player).where(
                    (models_elocaps.Player.user_id == user_id),
                    (models_elocaps.Player.mode == mode),
                ),
            )
        )
        .scalars()
        .first()
    )
    return player


async def add_player(db: AsyncSession, player: models_elocaps.Player) -> None:
    try:
        db.add(player)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def insert_player_into_game(
    db: AsyncSession,
    game_player: models_elocaps.GamePlayer,
) -> None:
    try:
        db.add(game_player)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def set_player_elo_gain(
    db: AsyncSession,
    game_player: models_elocaps.GamePlayer,
    gain: int,
) -> None:
    await db.execute(
        update(models_elocaps.GamePlayer)
        .where(
            models_elocaps.GamePlayer.player_id == game_player.player_id,
            models_elocaps.GamePlayer.game_id == game_player.game_id,
        )
        .values({"elo_gain": gain}),
    )
    await db.commit()


async def get_waiting_games(
    db: AsyncSession,
    user_id: str,
) -> Sequence[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .join(models_elocaps.GamePlayer)
        .join(models_elocaps.Player)
        .where(
            (models_elocaps.Player.user_id == user_id),
            not_(models_elocaps.GamePlayer.has_confirmed),
            not_(models_elocaps.Game.is_cancelled),
        ),
    )
    return result.scalars().all()


async def get_game_player(
    db: AsyncSession,
    game_id: str,
    user_id: str,
) -> models_elocaps.GamePlayer | None:
    return (
        (
            await db.execute(
                select(models_elocaps.GamePlayer)
                .join(models_elocaps.Player)
                .where(
                    (models_elocaps.Player.user_id == user_id),
                    (models_elocaps.GamePlayer.game_id == game_id),
                )
                .options(
                    selectinload(models_elocaps.GamePlayer.game).selectinload(
                        models_elocaps.Game.game_players,
                    ),
                ),
            )
        )
        .scalars()
        .first()
    )


async def user_game_validation(
    db: AsyncSession,
    game_player: models_elocaps.GamePlayer,
) -> None:
    game_player.has_confirmed = True
    await db.commit()


async def add_elo_to_player(db: AsyncSession, player_id: str, elo_gain: int) -> None:
    await db.execute(
        update(models_elocaps.Player)
        .where(models_elocaps.Player.id == player_id)
        .values({"elo": models_elocaps.Player.elo + elo_gain}),
    )


async def get_leaderboard(
    db: AsyncSession,
    game_mode: CapsMode,
    count=10,
) -> Sequence[models_elocaps.Player]:
    """Returns the `count` players who have the best elo in the given `game_mode`, in descending order"""
    result = await db.execute(
        select(models_elocaps.Player)
        .distinct()
        .join(models_elocaps.GamePlayer)
        .join(models_elocaps.Game)
        .where(
            not_(
                select(models_elocaps.GamePlayer)
                .correlate(models_elocaps.Game)
                .where(
                    (models_elocaps.GamePlayer.game_id == models_elocaps.Game.id),
                    not_(models_elocaps.GamePlayer.has_confirmed),
                )
                .exists(),
            ),
            (models_elocaps.Player.mode == game_mode),
        )
        .order_by(desc(models_elocaps.Player.elo))
        .limit(count)
        .options(selectinload(models_elocaps.Player.user)),
    )
    return result.scalars().all()


async def get_winrate(
    db: AsyncSession,
    game_mode: CapsMode,
    user_id: str,
) -> float | None:
    result = await db.execute(
        select(models_elocaps.Game)
        .join(models_elocaps.GamePlayer)
        .join(models_elocaps.Player)
        .where(
            (models_elocaps.Game.mode == game_mode),
            (models_elocaps.Player.user_id == user_id),
        )
        .options(
            selectinload(models_elocaps.Game.game_players).selectinload(
                models_elocaps.GamePlayer.player,
            ),
        ),
    )
    # We need to filter confirmed games in a loop instead of an SQL condition
    # because `is_confirmed` is a computed property
    games: list[models_elocaps.Game] = [
        x for x in result.scalars().all() if x.is_confirmed
    ]
    games_played = len(games)
    if games_played == 0:
        return None
    games_won = sum(1 for x in games if x.get_winner_team() == x.get_user_team(user_id))
    return round(games_won / games_played, 2)


async def cancel_game(db: AsyncSession, game: models_elocaps.Game) -> None:
    game.is_cancelled = True
    await db.commit()
