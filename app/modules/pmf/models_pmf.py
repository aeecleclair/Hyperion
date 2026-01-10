from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.pmf.types_pmf import LocationType, OfferType
from app.types.sqlalchemy import Base, PrimaryKey

if TYPE_CHECKING:
    from app.core.users.models_users import CoreUser


class OfferTags(Base):
    __tablename__ = "pmf_offer_tags"

    offer_id: Mapped[UUID] = mapped_column(
        ForeignKey("pmf_offers.id"),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(ForeignKey("pmf_tags.id"), primary_key=True)


class PmfOffer(Base):
    __tablename__ = "pmf_offers"

    id: Mapped[PrimaryKey]

    # TODO: Decide if the offer can remain if the author is deleted
    author_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    author: Mapped["CoreUser"] = relationship(
        init=False,
        lazy="joined",
        innerjoin=True,  # INNER JOIN since author_id is NOT NULL
    )

    company_name: Mapped[str]
    title: Mapped[str]
    description: Mapped[str]
    offer_type: Mapped[OfferType]
    location: Mapped[str]
    location_type: Mapped[LocationType]  # Enum (On_site, Hybrid, Remote)

    start_date: Mapped[date]
    end_date: Mapped[date]
    duration: Mapped[int]  # days

    tags: Mapped[list["OfferTags"]] = relationship(
        "Tags",
        back_populates="offers",
        lazy="selectin",  # Small collection
        secondary="pmf_offer_tags",
        default_factory=list,
    )


class Tags(Base):
    __tablename__ = "pmf_tags"

    id: Mapped[PrimaryKey]
    tag: Mapped[str]

    created_at: Mapped[date] = mapped_column(default=date.today)

    offers: Mapped[list["OfferTags"]] = relationship(
        "PmfOffer",
        back_populates="tags",
        secondary="pmf_offer_tags",
        default_factory=list,
    )
