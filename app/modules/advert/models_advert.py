from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from app.types.sqlalchemy import Base


class Advertiser(MappedAsDataclass, Base):
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


class Advert(MappedAsDataclass, Base):
    __tablename__ = "advert_adverts"

    id: Mapped[str] = mapped_column(primary_key=True)
    advertiser_id: Mapped[str] = mapped_column(ForeignKey("advert_advertisers.id"))
    title: Mapped[str]
    content: Mapped[str]
    date: Mapped[datetime]
    tags: Mapped[str | None]
    advertiser: Mapped[Advertiser] = relationship(
        "Advertiser",
        lazy="joined",
        back_populates="adverts",
    )
