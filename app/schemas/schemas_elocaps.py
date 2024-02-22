from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple
from app.utils.types.elocaps_types import CapsMode


class PlayerBase(BaseModel):
    user: CoreUserSimple
    elo: int
    mode: CapsMode

    class Config:
        orm_mode = True


class PlayerModeInfo(BaseModel):
    elo: int
    winrate: float | None


class DetailedPlayer(BaseModel):
    user: CoreUserSimple
    info: dict[CapsMode, PlayerModeInfo]


class GameMode(BaseModel):
    mode: CapsMode

    class Config:
        orm_mode = True


class GameCreateRequest(GameMode):
    players: list[GamePlayerBase]


class Game(GameMode):
    timestamp: datetime
    id: str
    game_players: list[GamePlayer]
    is_confirmed: bool
    cancelled: bool


class GamePlayerBase(BaseModel):
    user_id: str
    team: int
    score: int

    class Config:
        orm_mode = True


class GamePlayer(GamePlayerBase):
    elo_gain: int | None
    has_confirmed: bool
    user: CoreUserSimple


# Needed because these are created before GamePlayer is
Game.update_forward_refs()
GameCreateRequest.update_forward_refs()
