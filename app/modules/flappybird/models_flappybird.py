from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.users.models_users import CoreUser
from app.types.sqlalchemy import Base, PrimaryKey


class FlappyBirdScore(Base):
    __tablename__ = "flappy-bird_score"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    value: Mapped[int]
    creation_time: Mapped[datetime]


class FlappyBirdBestScore(Base):
    __tablename__ = "flappy-bird_best_score"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
    value: Mapped[int]
    creation_time: Mapped[datetime]
