"""Models file for music"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.models_core import CoreUser


class Musicians(Base):
    __tablename__ = "music_musicians"
    user_id: str = Column(String, ForeignKey("core_user.id"), primary_key=True)
    user: CoreUser = relationship(
        "CoreUser",
    )
    orchestra: bool = Column(Boolean)
    fanfare: bool = Column(Boolean)
    level: str = Column(String)
    looking_for: str = Column(String)
    # instruments : relation with "music_playing" table


class Instruments(Base):
    __tablename__ = "music_instruments"
    id: int = Column(Integer, primary_key=True)
    name: str = Column(String)


class Playing(Base):
    __tablename__ = "music_playing"
    instrument_id: int = Column(Integer, ForeignKey("music_instruments.id"))
    user_id: str = Column(String, ForeignKey("music_musicians.user_id"))
