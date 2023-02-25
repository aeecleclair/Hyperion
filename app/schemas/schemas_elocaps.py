from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple
from app.utils.types.elocaps_types import CapsMode


class PlayerBase(BaseModel):
    elo: int
    mode: CapsMode


class GameBase(BaseModel):
    mode: CapsMode


class GameCreateRequest(GameBase):
    players: list[GamePlayerBase]


class Game(GameBase):
    timestamp: datetime
    id: str
    players: list[GamePlayer]


class GamePlayerBase(BaseModel):
    user_id: str
    team: int
    quarters: int


class GamePlayer(GamePlayerBase):
    user: CoreUserSimple
