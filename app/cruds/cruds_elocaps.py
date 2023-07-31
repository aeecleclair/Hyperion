from datetime import date
from math import exp
from typing import Sequence

from sqlalchemy import desc, func, select
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
        select(models_elocaps.Player).where(models_elocaps.Player.user_id == user_id)
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


async def register_game(
    db: AsyncSession,
    game: models_elocaps.Game,
    game_players_info: list[schemas_elocaps.GamePlayerBase],
) -> None:
    try:
        db.add(game)
        await db.commit()
        for i in game_players_info:
            player = (
                (
                    await db.execute(
                        select(models_elocaps.Player).where(
                            (models_elocaps.Player.user_id == i.user_id)
                            & (models_elocaps.Player.mode == game.mode)
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not player:
                player = models_elocaps.Player(user_id=i.user_id, mode=game.mode)
                db.add(player)
                await db.commit()
            game_player = models_elocaps.GamePlayer(
                game_id=game.id, player_id=player.id, team=i.team, quarters=i.quarters
            )
            db.add(game_player)
            await db.commit()
        complete_game = (
            (
                await db.execute(
                    select(models_elocaps.Game)
                    .where(models_elocaps.Game.id == game.id)
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
        if complete_game is None:
            raise Exception("The game that was there just disappeared, we are screwed")
        else:
            game = complete_game
        for game_player in game.game_players:
            team = game_player.team
            c = game.get_team_quarters(~team + 4)
            s = game.get_team_quarters(team)
            a = game_player.quarters
            f = a * (1 - c / s) / (c + s)
            k = 15 * (2 - exp(-(f**2)))
            w = game.get_winner_team() == team
            d = game.get_team_elo(team) - game.get_team_elo(~team + 4)
            game_player.elo_gain = int(k * (w - 1 / (1 + 10 ** (-d / 400))))
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
            (models_elocaps.Player.user_id == user_id)
            & ~models_elocaps.GamePlayer.has_confirmed
        )
        .options(
            selectinload(models_elocaps.Game.game_players)
            .selectinload(models_elocaps.GamePlayer.player)
            .selectinload(models_elocaps.GamePlayer.game)
        )
    )
    return [i.game for i in result.scalars().all()]


async def confirm_game(db: AsyncSession, game_id: str, user_id: str) -> None:
    game_player: models_elocaps.GamePlayer | None = (
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
    if game_player is None:
        raise ValueError("This player has not played in here")
    game_player.has_confirmed = True
    await db.commit()
    if game_player.game.is_confirmed:
        await end_game(db, game_id)


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
    for i in game.game_players:
        i.player.elo += i.elo_gain
    await db.commit()


async def get_leaderboard(
    db: AsyncSession, game_mode: CapsMode, count=10
) -> Sequence[models_elocaps.Player]:
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
        i for i in result.scalars().all() if i.is_confirmed
    ]
    return sum(
        1 for i in games if i.get_winner_team() == i.get_user_team(user_id)
    ) / len(games)
