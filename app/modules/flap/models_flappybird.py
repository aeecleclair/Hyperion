from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.models_core import CoreUser


class FlappyBirdScore(Base):
    __tablename__ = "flappy-bird_score"

    id: str = Column(String, primary_key=True, index=True)

    user_id: str = Column(String, ForeignKey("core_user.id"), nullable=False)
    user: CoreUser = relationship("CoreUser")
    value: int = Column(Integer, nullable=False)
    creation_time: datetime = Column(DateTime, nullable=False)
