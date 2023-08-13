from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import relationship

from app.database import Base


class Advert(Base):
    __tablename__ = "advert"

    id: str = Column(String, primary_key=True, nullable=False)
    title: str = Column(String, nullable=False)
    content: str = Column(String, nullable=False)
    date: datetime = Column(DateTime(timezone=True), nullable=False)
    author: int = Column(String, nullable=False)
    tags: str = Column(list, nullable=True)
    lists: list["Tags"] = relationship("Tags", back_populates="advert")


class Tags(Base):
    __tablename__ = "advert_tags"

    id: str = Column(String, primary_key=True, nullable=False)
    name: str = Column(String, nullable=False)
    couleur: str = Column(String, nullable=False)
