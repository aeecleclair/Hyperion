from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple
from app.utils.types.elocaps_types import CapsMode


class PlayerBase(BaseModel):
    user_id: str
    elo: int
    mode: CapsMode

    class Config:
        orm_mode = True


class GameBase(BaseModel):
    mode: CapsMode

    class Config:
        orm_mode = True


class GameCreateRequest(GameBase):
    players: list[GamePlayerBase]


class Game(GameBase):
    timestamp: datetime
    id: str
    game_players: list[GamePlayer]
    is_confirmed: bool


class GamePlayerBase(BaseModel):
    user_id: str
    team: int
    quarters: int

    class Config:
        orm_mode = True


class GamePlayer(GamePlayerBase):
    elo_gain: int | None
    user: CoreUserSimple


Game.update_forward_refs()
GameCreateRequest.update_forward_refs()
