from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models_core import CoreUser
from app.types.sqlalchemy import Base, PrimaryKey


class FlappyBirdScore(Base):
    __tablename__ = "flappy-bird_score"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser")
    value: Mapped[int]
    creation_time: Mapped[datetime]

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __eq__(self, value: object) -> bool:
        if isinstance(value, FlappyBirdScore):
            return self.to_dict() == value.to_dict()
        else:
            return False


class FlappyBirdBestScore(Base):
    __tablename__ = "flappy-bird_best_score"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    user: Mapped[CoreUser] = relationship("CoreUser")
    value: Mapped[int]
    creation_time: Mapped[datetime]

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __eq__(self, value: object) -> bool:
        if isinstance(value, FlappyBirdBestScore):
            return self.to_dict() == value.to_dict()
        else:
            return False
