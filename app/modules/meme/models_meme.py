import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models_core import CoreUser
from app.modules.meme.types_meme import MemeStatus
from app.types.sqlalchemy import Base, PrimaryKey


class Vote(Base):
    __tablename__ = "meme_vote"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    meme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meme_meme.id"))
    meme: Mapped["Meme"] = relationship(
        "Meme",
        init=False,
        back_populates="votes",
        lazy="selectin",
    )
    positive: Mapped[bool]


class Meme(Base):
    __tablename__ = "meme_meme"

    id: Mapped[PrimaryKey]
    status: Mapped[MemeStatus]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    creation_time: Mapped[datetime]
    vote_score: Mapped[int]
    votes: Mapped[list["Vote"]] = relationship(
        "Vote",
        default_factory=list,
        lazy="selectin",
        back_populates="meme",
    )


class Ban(Base):
    __tablename__ = "meme_ban"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship(
        "CoreUser",
        init=False,
        foreign_keys=[user_id],
    )
    creation_time: Mapped[datetime]
    end_time: Mapped[datetime | None]
    admin_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    admin: Mapped[CoreUser] = relationship(
        "CoreUser",
        init=False,
        foreign_keys=[admin_id],
    )
