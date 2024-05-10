from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models_core import CoreUser
from app.types.sqlalchemy import Base, TZDateTime


class FlappyBirdScore(Base):
    __tablename__ = "flappy-bird_score"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("core_user.id"),
        nullable=False,
    )
    user: Mapped[CoreUser] = relationship("CoreUser")
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    creation_time: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
