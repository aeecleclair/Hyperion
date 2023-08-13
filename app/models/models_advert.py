from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base


class Advertiser(Base):
    __tablename__ = "advert_advertiser"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, nullable=False, unique=True)
    group_manager_id: str = Column(String, nullable=False)

    adverts: list["Advert"] = relationship(
        "Advert", lazy="joined", back_populates="advertiser"
    )


class Advert(Base):
    __tablename__ = "advert_adverts"

    id: str = Column(String, primary_key=True, nullable=False)
    advertiser_id: str = Column(ForeignKey("advert_advertiser.id"))
    advertiser: Advertiser = relationship(
        "Advertiser",
        lazy="joined",
        back_populates="adverts",
    )
    title: str = Column(String, nullable=False)
    content: str = Column(String, nullable=False)
    date: datetime = Column(DateTime(timezone=True), nullable=False)
    # tags_links: list["Tag"] = relationship("AdvertsTagsLink", back_populates="advert")


"""
class Tag(Base):
    __tablename__ = "advert_tags"

    id: str = Column(String, primary_key=True, nullable=False)
    name: str = Column(String, nullable=False)
    couleur: str = Column(String, nullable=False)

    adverts_links: list["AdvertsTagsLink"] = relationship(
        "AdvertsTagsLink", back_populates="tag"
    )


class AdvertsTagsLink(Base):
    __tablename__ = "adverts_tags_link"

    id: str = Column(String, primary_key=True, nullable=False)
    advert_id: str = Column(String, ForeignKey("adverts.id"))
    tag_id: str = Column(String, ForeignKey("advert_tags.id"))
    advert: Advert = relationship("Advert", lazy="joined", back_populates="tags_links")
    tag: Tag = relationship("Tag", lazy="joined", back_populates="adverts_links")
"""
