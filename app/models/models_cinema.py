from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class Session(Base):
    __tablename__ = "cinema_session"

    id: str = Column(String, primary_key=True, nullable=False)
    name: str = Column(String, nullable=False)
    start: datetime = Column(DateTime, nullable=False)
    duration: int = Column(Integer, nullable=False)
    overview: str = Column(String, nullable=True)
    poster_url: str = Column(String, nullable=True)
    genre: str = Column(String, nullable=True)
    tagline: str = Column(String, nullable=True)
