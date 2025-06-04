from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.types.sqlalchemy import Base


class Advertiser(Base):
    __tablename__ = "advert_advertisers"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True)
    group_manager_id: Mapped[str]

    adverts: Mapped[list["Advert"]] = relationship(
        "Advert",
        lazy="subquery",
        back_populates="advertiser",
        default_factory=list,
    )


class Advert(Base):
    __tablename__ = "advert_adverts"

    id: Mapped[str] = mapped_column(primary_key=True)
    advertiser_id: Mapped[str] = mapped_column(ForeignKey("advert_advertisers.id"))
    advert_type: Mapped[str]
    title: Mapped[str]
    content: Mapped[str]
    release_date: Mapped[datetime] # The date when the advert will be released
    start_date: Mapped[datetime | None] # The date when an event starts for example
    end_date: Mapped[datetime | None] # The date when an event ends for example
    date: Mapped[datetime] # The date when the advert was created
    tags: Mapped[str | None]
    advertiser: Mapped[Advertiser] = relationship(
        "Advertiser",
        lazy="joined",
        back_populates="adverts",
    )
