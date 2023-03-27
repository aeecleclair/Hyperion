from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models import models_core
from app.utils.types.elocaps_types import CapsMode


class Player(Base):
    __tablename__ = "elocaps_player"

    # Needed because relationships are awful and don't even work if it's not there
    id: str = Column(
        String, primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    user_id: str = Column(ForeignKey("core_user.id"), nullable=False)
    mode: CapsMode = Column(Enum(CapsMode), nullable=False)
    # User id and mode should be unique
    elo: int = Column(Integer, nullable=False, default=1000)

    user: models_core.CoreUser = relationship("CoreUser")
    game_players: GamePlayer = relationship("GamePlayer", back_populates="player")


class Game(Base):
    __tablename__ = "elocaps_game"

    id: str = Column(
        String, primary_key=True, nullable=False, default=lambda: str(uuid4())
    )
    timestamp: datetime = Column(DateTime, nullable=False, default=func.now())
    mode: CapsMode = Column(Enum(CapsMode), nullable=False)

    game_players: list[GamePlayer] = relationship("GamePlayer", back_populates="game")

    @property
    def is_confirmed(self) -> bool:
        return all([i.has_confirmed for i in self.game_players])

    def get_team_quarters(self, team: int) -> int:
        return sum(i.quarters for i in self.game_players if i.team == team)

    def get_team_elo(self, team: int) -> float:
        players_elo = [i.player.elo for i in self.game_players if i.team == team]
        return sum(players_elo) / len(players_elo)

    def get_user_team(self, user_id: str) -> int:
        return next(i for i in self.game_players if i.player.user_id == user_id).team

    def get_winner_team(self) -> int:
        return max(
            ((i, self.get_team_quarters(i)) for i in range(2)), key=lambda x: x[1]
        )[0]


class GamePlayer(Base):
    __tablename__ = "elocaps_game_player"

    game_id: str = Column(
        ForeignKey("elocaps_game.id"), nullable=False, primary_key=True
    )
    player_id: str = Column(
        ForeignKey("elocaps_player.id"), nullable=False, primary_key=True
    )
    team: int = Column(Integer, nullable=False)
    quarters: int = Column(Integer, nullable=False)
    has_confirmed: bool = Column(Boolean, nullable=False, default=False)
    elo_gain: int = Column(Integer, nullable=False, default=0)

    game: Game = relationship("Game", viewonly=True)
    player: Player = relationship(
        "Player", uselist=False, back_populates="game_players"
    )

    @property
    def user_id(self) -> str:
        return self.player.user_id

    @property
    def user(self) -> models_core.CoreUser:
        return self.player.user
