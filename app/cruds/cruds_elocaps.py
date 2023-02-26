from datetime import date
from math import exp

from sqlalchemy import select, desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_elocaps
from app.utils.types.elocaps_types import CapsMode


async def get_latest_games(db: AsyncSession, count=10) -> list[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .order_by(desc(models_elocaps.Game.timestamp))
        .options(
            selectinload(models_elocaps.Game.players).selectinload(
                models_elocaps.GamePlayer.user
            )
        )
        .limit(count)
    )
    return result.scalars().all()


async def get_games_played_on(
    db: AsyncSession, time: date
) -> list[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.Game)
        .where(func.DATE(models_elocaps.Game.timestamp) == time)
        .options(
            selectinload(models_elocaps.Game.players).selectinload(
                models_elocaps.GamePlayer.user
            )
        )
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
        .options(
            selectinload(models_elocaps.GamePlayer.game)
            .selectinload(models_elocaps.Game.players)
            .selectinload(models_elocaps.GamePlayer.user)
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
            selectinload(models_elocaps.Game.players).selectinload(
                models_elocaps.GamePlayer.user
            )
        )
    )
    return result.scalars().first()


async def register_game(
    db: AsyncSession,
    game: models_elocaps.Game,
    game_players: list[models_elocaps.GamePlayer],
) -> None:
    db.add(game)
    try:
        await db.commit()
        for i in game_players:
            i.game_id = game.id
        db.add_all(game_players)
        await db.commit()
        game_data = (
            await db.execute(
                select(
                    models_elocaps.Game,
                    models_elocaps.GamePlayer,
                    models_elocaps.Player,
                )
                .where(models_elocaps.Game.id == game.id)
                .join(
                    models_elocaps.GamePlayer,
                    models_elocaps.GamePlayer.game_id == models_elocaps.Game.id,
                )
                .join(
                    models_elocaps.Player,
                    (models_elocaps.Player.user_id == models_elocaps.GamePlayer.user_id)
                    & (models_elocaps.Player.mode == models_elocaps.Game.mode),
                    isouter=True,
                )
                .options(selectinload(models_elocaps.Game.players))
            )
        ).all()
        game = game_data[0].Game

        def get_team_elo(team: int) -> float:
            team_members_elos = [
                i.Player.elo if i.Player else 1000
                for i in game_data
                if i.GamePlayer.team == team
            ]
            return sum(team_members_elos) / len(team_members_elos)

        for i in game_data:
            team = i.GamePlayer.team
            c = game.get_team_quarters(~team + 4)
            d = game.get_team_quarters(team)
            a = i.GamePlayer.quarters
            f = a * (1 - c / d) / (c + d)
            k = 15 * (2 - exp(-(f**2)))
            w = game.get_winner_team() == team
            d = get_team_elo(team) - get_team_elo(~team + 4)
            i.GamePlayer.elo_gain = int(k * (w - 1 / (1 + 10 ** (-d / 400))))
            await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_waiting_games(
    db: AsyncSession, user_id: str
) -> list[models_elocaps.Game]:
    result = await db.execute(
        select(models_elocaps.GamePlayer)
        .where(
            (models_elocaps.GamePlayer.user_id == user_id)
            & ~models_elocaps.GamePlayer.has_confirmed
        )
        .options(
            selectinload(models_elocaps.Game.players).selectinload(
                models_elocaps.GamePlayer.user
            )
        )
    )
    return [i.game for i in result.scalars().all()]


async def confirm_game(db: AsyncSession, game_id: str, user_id: str) -> None:
    result = await db.execute(
        select(models_elocaps.GamePlayer).where(
            (models_elocaps.GamePlayer.user_id == user_id)
        )
        & (models_elocaps.GamePlayer.game_id == game_id)
    )
    result.scalars().first().has_confirmed = False
    await db.commit()


async def end_game(db: AsyncSession, game_id: str) -> None:
    result = await db.execute(
        select(models_elocaps.Game)
        .where(models_elocaps.Game.id == game_id)
        .options(selectinload(models_elocaps.Game.players))
    )
    game: models_elocaps.Game = result.scalars().first()


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


async def get_winrate(
    db: AsyncSession,
    game_mode: CapsMode,
    user_id: str,
) -> float:
    result = await db.execute(
        (
            select(models_elocaps.Game)
            .where(
                (models_elocaps.Game.mode == game_mode)
                & (models_elocaps.GamePlayer.user_id == user_id)
            )
            .options(selectinload(models_elocaps.Game.players))
        )
    )
    games: list[models_elocaps.Game] = [
        i for i in result.scalars().all() if i.is_confirmed
    ]
    return sum(
        1 for i in games if i.get_winner_team() == i.get_user_team(user_id)
    ) / len(games)
