from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.schemas_core import CoreUserSimple
from app.modules.elocaps.types_elocaps import CapsMode


class PlayerBase(BaseModel):
    user: CoreUserSimple
    elo: int
    mode: CapsMode

    model_config = ConfigDict(from_attributes=True)


class PlayerModeInfo(BaseModel):
    elo: int
    winrate: float | None


class DetailedPlayer(BaseModel):
    user: CoreUserSimple
    info: dict[CapsMode, PlayerModeInfo]


class GameMode(BaseModel):
    mode: CapsMode

    model_config = ConfigDict(from_attributes=True)


class GameCreateRequest(GameMode):
    players: list[GamePlayerBase]


class Game(GameMode):
    timestamp: datetime
    id: str
    game_players: list[GamePlayer]
    is_confirmed: bool
    is_cancelled: bool


class GamePlayerBase(BaseModel):
    user_id: str
    team: int
    score: int

    model_config = ConfigDict(from_attributes=True)


class GamePlayer(GamePlayerBase):
    elo_gain: int | None
    has_confirmed: bool
    user: CoreUserSimple


# Needed because these are created before GamePlayer is
Game.model_rebuild()
GameCreateRequest.model_rebuild()
