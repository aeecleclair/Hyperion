from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_elocaps
from app.dependencies import get_db, is_user_a_member
from app.models import models_core, models_elocaps
from app.schemas import schemas_elocaps
from app.utils.types.elocaps_types import CapsMode
from app.utils.types.tags import Tags

router = APIRouter()


@router.post(
    "/elocaps/games",
    status_code=201,
    response_model=schemas_elocaps.Game,
    tags=[Tags.elocaps],
)
async def register_game(
    game_params: schemas_elocaps.GameCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    if not any(user.id == i.user_id for i in game_params.players):
        raise HTTPException(400, "You must be part of the game")
    game = models_elocaps.Game(mode=game_params.mode)
    try:
        await cruds_elocaps.register_game(db, game, game_params.players)
        return await cruds_elocaps.get_game_details(db, game.id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get(
    "/elocaps/games/latest",
    response_model=list[schemas_elocaps.Game],
    status_code=200,
    tags=[Tags.elocaps],
)
async def get_latest_games(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_elocaps.get_latest_games(db)


@router.get(
    "/elocaps/games/waiting",
    response_model=list[schemas_elocaps.GameMode],
    status_code=200,
    tags=[Tags.elocaps],
)
async def get_waiting_games(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_elocaps.get_waiting_games(db, user.id)


@router.get(
    "/elocaps/games",
    response_model=list[schemas_elocaps.Game],
    status_code=200,
    tags=[Tags.elocaps],
)
async def get_games_played_on(
    time: date,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_elocaps.get_games_played_on(db, time)


@router.get(
    "/elocaps/games/{game_id}",
    response_model=schemas_elocaps.Game,
    status_code=200,
    tags=[Tags.elocaps],
)
async def get_game_detail(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    game = await cruds_elocaps.get_game_details(db, game_id)
    if game is None:
        raise HTTPException(404, "Game not found")
    return game


@router.post(
    "/elocaps/games/{game_id}/validate",
    status_code=201,
    response_model=schemas_elocaps.Game,
    tags=[Tags.elocaps],
)
async def confirm_game(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    try:
        await cruds_elocaps.confirm_game(db, game_id=game_id, user_id=user.id)
        return await cruds_elocaps.get_game_details(db, game_id)
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.get(
    "/elocaps/players/{user_id}/games",
    response_model=list[schemas_elocaps.Game],
    status_code=200,
    tags=[Tags.elocaps],
)
async def get_player_games(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_elocaps.get_player_games(db, user_id)


@router.get(
    "/elocaps/players/{user_id}",
    response_model=schemas_elocaps.DetailedPlayer,
    status_code=200,
    tags=[Tags.elocaps],
)
async def get_player_info(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    db_player_modes = await cruds_elocaps.get_player_info(db, user_id)
    mode_info = {
        x.mode: schemas_elocaps.PlayerModeInfo(
            elo=x.elo, winrate=await cruds_elocaps.get_winrate(db, x.mode, user_id)
        )
        for x in db_player_modes
    }
    return schemas_elocaps.DetailedPlayer(user=db_player_modes[0].user, info=mode_info)


@router.get(
    "/elocaps/leaderboard",
    response_model=list[schemas_elocaps.PlayerBase],
    status_code=200,
    tags=[Tags.elocaps],
)
async def get_leaderboard(
    mode: CapsMode,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_elocaps.get_leaderboard(db, mode)
