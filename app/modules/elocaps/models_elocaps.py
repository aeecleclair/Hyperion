from __future__ import (  # Permit the use of class names not declared yet in the annotations
    annotations,
)

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import models_core
from app.database import Base
from app.modules.elocaps.types_elocaps import CapsMode


class Player(Base):
    __tablename__ = "elocaps_player"

    # Needed because relationships are awful and don't even work if it's not there
    id: Mapped[str] = mapped_column(
        String, primary_key=True, nullable=False, default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), nullable=False)
    mode: Mapped[CapsMode] = mapped_column(Enum(CapsMode), nullable=False)
    # User id and mode should be unique
    elo: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)

    user: Mapped[models_core.CoreUser] = relationship("CoreUser")
    game_players: Mapped[list[GamePlayer]] = relationship(
        "GamePlayer", back_populates="player",
    )


class Game(Base):
    __tablename__ = "elocaps_game"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, nullable=False, default=lambda: str(uuid4()),
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(),
    )
    mode: Mapped[CapsMode] = mapped_column(Enum(CapsMode), nullable=False)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    game_players: Mapped[list[GamePlayer]] = relationship(
        "GamePlayer", back_populates="game",
    )

    @property
    def is_confirmed(self) -> bool:
        return all([i.has_confirmed for i in self.game_players])

    def get_team_score(self, team: int) -> float:
        """Returns 0, 0.5, or 1."""
        players = [i for i in self.game_players if i.team == team]
        return (sum(i.score for i in players) / len(players) + 1) / 2

    def get_team_elo(self, team: int) -> float:
        players_elo = [i.player.elo for i in self.game_players if i.team == team]
        return sum(players_elo) / len(players_elo)

    def get_user_team(self, user_id: str) -> int:
        return next(i for i in self.game_players if i.player.user_id == user_id).team

    def get_winner_team(self) -> int:
        return max(((i, self.get_team_score(i)) for i in [1, 2]), key=lambda x: x[1])[0]


class GamePlayer(Base):
    __tablename__ = "elocaps_game_player"

    game_id: Mapped[str] = mapped_column(
        ForeignKey("elocaps_game.id"), nullable=False, primary_key=True,
    )
    player_id: Mapped[str] = mapped_column(
        ForeignKey("elocaps_player.id"), nullable=False, primary_key=True,
    )
    team: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    has_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    elo_gain: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    game: Mapped[Game] = relationship("Game")
    player: Mapped[Player] = relationship(
        "Player", uselist=False, back_populates="game_players",
    )

    @property
    def user_id(self) -> str:
        return self.player.user_id

    @property
    def user(self) -> models_core.CoreUser:
        return self.player.user
