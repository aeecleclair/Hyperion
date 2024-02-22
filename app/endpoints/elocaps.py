from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_elocaps
from app.dependencies import get_db, is_user_a_member
from app.models import models_core, models_elocaps
from app.schemas import schemas_elocaps
from app.utils.tools import compute_elo_gain
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
    if all(
        user.id != player.user_id for player in game_params.players
    ):  # User is not part of players
        raise HTTPException(400, "You must be part of the game")
    for player in game_params.players:
        for sub_player in game_params.players:
            if player != sub_player and player.user_id == sub_player.user_id:
                raise HTTPException(400, "You can't have the same player twice")
    game = models_elocaps.Game(mode=game_params.mode)
    try:
        await cruds_elocaps.create_game(db, game)
        for player in game_params.players:
            await cruds_elocaps.insert_player_into_game(db, game, player)
        complete_game = await cruds_elocaps.get_game_details(db, game.id)
        # Since it has just been inserted, it should still be there
        assert complete_game is not None
        for game_player in complete_game.game_players:
            team = game_player.team
            elo_gain = round(
                compute_elo_gain(
                    complete_game.get_team_score(team),
                    20,
                    complete_game.get_team_elo(team),
                    complete_game.get_team_elo(-team + 3),
                )
            )
            await cruds_elocaps.set_player_elo_gain(db, game_player, elo_gain)
        creator = await cruds_elocaps.get_game_player(db, game.id, user.id)
        assert creator is not None
        await cruds_elocaps.user_game_validation(db, creator)
        return complete_game
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
        player = await cruds_elocaps.get_game_player(
            db, game_id=game_id, user_id=user.id
        )
        if not player:
            raise HTTPException(
                400, "You are not part of that game, or it doesn't exist"
            )
        if player.game.cancelled:
            raise HTTPException(400, "This game has been cancelled")
        await cruds_elocaps.user_game_validation(db, player)
        if player.game.is_confirmed:
            await cruds_elocaps.end_game(db, game_id)
        return await cruds_elocaps.get_game_details(db, game_id)
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.post(
    "/elocaps/games/{game_id}/cancel",
    status_code=201,
    response_model=schemas_elocaps.Game,
    tags=[Tags.elocaps],
)
async def cancel_game(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    player = await cruds_elocaps.get_game_player(db, game_id=game_id, user_id=user.id)
    if not player:
        raise HTTPException(400, "You are not part of that game, or it doesn't exist")
    if player.game.is_confirmed:
        raise HTTPException(400, "This game has already been confirmed")
    await cruds_elocaps.cancel_game(db, player.game)
    return await cruds_elocaps.get_game_details(db, game_id)


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
    # Build a DetailedPlayer object (a dict that looks like {mode: {elo, winrate}})
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
