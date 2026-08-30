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
    duration: Mapped[int]  # days

    created_on: Mapped[date] = mapped_column(insert_default=date.today)
    hidden: Mapped[bool]
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        back_populates="offers",
        lazy="selectin",  # Small collection
        secondary="pmf_offer_tags",
        default_factory=list,
    )

class Tag(Base):
    __tablename__ = "pmf_tags"

    id: Mapped[PrimaryKey]
    tag: Mapped[str]

    created_on: Mapped[date] = mapped_column(insert_default=date.today)

    offers: Mapped[list["PmfOffer"]] = relationship(
        "PmfOffer",
        back_populates="tags",
        secondary="pmf_offer_tags",
        default_factory=list,
    )

class Profile(Base):
    __tablename__ = "pmf_profiles"

    user_id: Mapped[PrimaryKey] = mapped_column(ForeignKey("core_user.id"))
    cv_list: Mapped[list["Cv"]] = relationship(
        "Cv",
        back_populates="profile",
        default_factory=list,
        lazy="selectin"
    )

class Cv(Base):
    __tablename__ = "pmf_cvs"

    name: Mapped[str]
    user_id: Mapped[str] = mapped_column(ForeignKey("pmf_profiles.user_id"))
    id: Mapped[PrimaryKey]
    created_on: Mapped[date] = mapped_column(insert_default=date.today)
    profile: Mapped["Profile"] = relationship(
        "Profile",
        back_populates="cv_list",
        init=False
    )
    allowed_users: Mapped[list["CoreUser"]] = relationship(
        "CoreUser",
        lazy="selectin",  # Small collection
        secondary="pmf_applications",
        default_factory=list,
        )

class Application(Base):
    __tablename__ = "pmf_applications"
    motivation=Mapped[str]
    cv_id: Mapped[UUID] = mapped_column(ForeignKey("pmf_cvs.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("pmf_profiles.user_id"), primary_key=True)
    alumni_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    offer_id: Mapped[str] = mapped_column(ForeignKey("pmf_offers.id"), primary_key=True)
    created_on: Mapped[date]