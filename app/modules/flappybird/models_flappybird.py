from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from app.core.models_core import CoreUser
from app.types.sqlalchemy import Base, PrimaryKey


class FlappyBirdScore(MappedAsDataclass, Base):
    __tablename__ = "flappy-bird_score"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    value: Mapped[int]
    creation_time: Mapped[datetime]


class FlappyBirdBestScore(MappedAsDataclass, Base):
    __tablename__ = "flappy-bird_best_score"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    value: Mapped[int]
    creation_time: Mapped[datetime]
