from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Enum,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models import models_core
from app.utils.types.elocaps_types import CapsMode


class Player(Base):
    __tablename__ = "elocaps_player"

    user_id: str = Column(ForeignKey("core_user.id"), primary_key=True, nullable=False)
    elo: int = Column(Integer, nullable=False)
    mode: CapsMode = Column(Enum(CapsMode), nullable=False, primary_key=True)

    user: models_core.CoreUser = relationship("CoreUser")


class Game(Base):
    __tablename__ = "elocaps_game"

    id: str = Column(
        String, primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    timestamp: datetime = Column(DateTime, nullable=False, default=func.now())
    mode: CapsMode = Column(Enum(CapsMode), nullable=False)

    players: list[GamePlayer] = relationship("GamePlayer")


class GamePlayer(Base):
    __tablename__ = "elocaps_game_player"

    game_id: str = Column(
        ForeignKey("elocaps_game.id"), nullable=False, primary_key=True
    )
    user_id: str = Column(ForeignKey("core_user.id"), nullable=False, primary_key=True)
    team: int = Column(Integer, nullable=False)
    quarters: int = Column(Integer, nullable=False)

    game: Game = relationship("Game")
