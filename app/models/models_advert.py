from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import relationship

from app.database import Base


class Advertiser(Base):
    __tablename__ = "advertiser"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, nullable=False, unique=True)
    group_manager_id: str = Column(String, nullable=False)

    adverts: list["Advert"] = relationship(
        "Advert", lazy="joined", back_populates="advertiser"
    )


class Advert(Base):
    __tablename__ = "adverts"

    id: str = Column(String, primary_key=True, nullable=False)
    title: str = Column(String, nullable=False)
    content: str = Column(String, nullable=False)
    date: datetime = Column(DateTime(timezone=True), nullable=False)
    co_advertisers: list["Advertiser"] = relationship(
        "Advertiser", back_populates="adverts"
    )
    tags: list["Tags"] = relationship("Tags", back_populates="adverts")
    advertiser: Advertiser = relationship(
        "Advertiser",
        lazy="joined",
        back_populates="adverts",
    )


class Tags(Base):
    __tablename__ = "advert_tags"

    id: str = Column(String, primary_key=True, nullable=False)
    name: str = Column(String, nullable=False)
    couleur: str = Column(String, nullable=False)
    group_manager_id: str = Column(String, nullable=False)
