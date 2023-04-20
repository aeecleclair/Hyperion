from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base


class Advertiser(Base):
    __tablename__ = "advert_advertisers"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, nullable=False, unique=True)
    group_manager_id: str = Column(String, nullable=False)

    adverts: list["Advert"] = relationship(
        "Advert", lazy="subquery", back_populates="advertiser"
    )
    coadverts: list["Advert"] = relationship(
        "Advert", secondary="advert_coadvertise_content", back_populates="coadvertisers"
    )


class Advert(Base):
    __tablename__ = "advert_adverts"

    id: str = Column(String, primary_key=True, nullable=False)
    advertiser_id: str = Column(ForeignKey("advert_advertisers.id"))
    advertiser: Advertiser = relationship(
        "Advertiser",
        lazy="joined",
        back_populates="adverts",
    )
    title: str = Column(String, nullable=False)
    content: str = Column(String, nullable=False)
    date: datetime = Column(DateTime(timezone=True), nullable=False)
    tags: str = Column(String, nullable=True)
    coadvertisers: list["Advert"] = relationship(
        "Advertiser", secondary="advert_coadvertise_content", back_populates="coadverts"
    )


class CoAdvertContent(Base):
    __tablename__ = "advert_coadvertise_content"
    coadvertiser_id: str = Column(ForeignKey("advert_advertisers.id"), primary_key=True)
    advert_id: str = Column(ForeignKey("advert_adverts.id"), primary_key=True)
