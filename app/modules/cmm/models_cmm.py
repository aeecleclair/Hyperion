from datetime import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models_core import CoreUser

if TYPE_CHECKING:
    from app.modules.cmm.models_cmm import Meme

from app.modules.cmm.types_cmm import MemeStatus
from app.types.sqlalchemy import Base, PrimaryKey


class Report(Base):
    __tablename__ = "cmm_report"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    creation_time: Mapped[datetime]
    meme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cmm_meme.id"))
    meme: Mapped[Meme] = relationship("Meme", init=False)
    description: Mapped[str | None] = mapped_column(default=None)


class Vote(Base):
    ___tablename___ = "cmm_vote"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    creation_time: Mapped[datetime]
    meme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cmm_meme.id"))
    meme: Mapped[Meme] = relationship("Meme", init=False)
    positive: bool


class Meme(Base):
    __tablename__ = "cmm_meme"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    creation_time: Mapped[datetime]
    vote_score: Mapped[int]
    votes: Mapped[list[Vote]] = relationship(
        "Votes",
        secondary="cmm_vote",
        lazy="selectin",
        default_factory=list,
    )
    status: Mapped[MemeStatus]
    reports: Mapped[list[Report]] = relationship(
        "Report",
        secondary="cmm_report",
        lazy="selectin",
        default_factory=list,
    )
