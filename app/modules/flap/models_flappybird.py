from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.database import Base


class FlappyBirdScore(Base):
    __tablename__ = "flappy-bird_score"

    id: str = Column(String, primary_key=True, index=True)
    user_id: str = Column(String, index=True, nullable=False)
    value: str = Column(String, nullable=False)
    creation_time: datetime = Column(DateTime, nullable=False)
