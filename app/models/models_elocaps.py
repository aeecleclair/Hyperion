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
    Boolean,
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

    players: list[GamePlayer] = relationship("GamePlayer", back_populates="game")

    @property
    def is_confirmed(self) -> bool:
        return all([i.has_confirmed for i in self.players])

    def get_team_quarters(self, team: int) -> int:
        return sum(i.quarters for i in self.players if i.team == team)

    def get_user_team(self, user_id: str) -> int:
        return next(i for i in self.players if i.user_id == user_id).team

    def get_winner_team(self) -> int:
        return max(
            ((i, self.get_team_quarters(i)) for i in range(2)), key=lambda x: x[1]
        )[0]


class GamePlayer(Base):
    __tablename__ = "elocaps_game_player"

    game_id: str = Column(
        ForeignKey("elocaps_game.id"), nullable=False, primary_key=True
    )
    user_id: str = Column(ForeignKey("core_user.id"), nullable=False, primary_key=True)
    team: int = Column(Integer, nullable=False)
    quarters: int = Column(Integer, nullable=False)
    has_confirmed: bool = Column(Boolean, nullable=False, default=False)
    elo_gain: int = Column(Integer)

    game: Game = relationship("Game", viewonly=True)
    user: models_core.CoreUser = relationship("CoreUser")
    """player: Player = relationship(
        "Player",
        secondary="elocaps_game",
        viewonly=True,
        primaryjoin="GamePlayer.user_id == foreign(Player.user_id)",
        secondaryjoin="(GamePlayer.game_id == foreign(Game.id)) & (Game.mode == foreign(Player.mode))"
    )"""
