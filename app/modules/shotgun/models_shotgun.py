import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.core.models_core import CoreGroup, CoreUser

from app.types.sqlalchemy import Base, PrimaryKey


class ShotgunOrganizer(Base):
    __tablename__ = "shotgun_organizer"

    id: Mapped[PrimaryKey]
    group_id: Mapped[str] = mapped_column(
        ForeignKey("core_group.id"),
    )
    user: Mapped["CoreGroup"] = relationship("CoreGroup")


class ShotgunSession(Base):
    __tablename__ = "shotgun_session"

    id: Mapped[PrimaryKey]

    organizer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shotgun_organizer.id"),
    )
    name: Mapped[str]
    description: Mapped[str | None]
    start: Mapped[datetime]
    end: Mapped[datetime | None]
    quantity: Mapped[int] = mapped_column(default=0)
    price: Mapped[int]


class ShotgunTicketGenerator(Base):
    __tablename__ = "shotgun_ticket_generator"

    id: Mapped[PrimaryKey]
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shotgun_session.id"),
    )
    name: Mapped[str]
    max_use: Mapped[int]
    expiration: Mapped[datetime]


class ShotgunTicket(Base):
    __tablename__ = "shotgun_ticket"
    id: Mapped[PrimaryKey]
    secret: Mapped[uuid.UUID] = mapped_column(unique=True)
    generator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shotgun_ticket_generator.id"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shotgun_session.id"),
    )
    session: Mapped["ShotgunSession"] = relationship("ShotgunSession")
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    name: Mapped[str]
    user: Mapped["CoreUser"] = relationship("CoreUser")
    scan_left: Mapped[int]
    tags: Mapped[str]
    expiration: Mapped[datetime]


class ShotgunPurchase(Base):
    """
    HelloAsso links expire after 15 Minutes. Hence, an unpaid purchase will be considered expired after 16 minutes and deleted on next check.
    """

    __tablename__ = "shotgun_purchase"

    id: Mapped[PrimaryKey]
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shotgun_session.id"),
    )
    user_id = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )
    checkout_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_checkout.id"))
    purchased_on: Mapped[datetime]
    paid: Mapped[bool]
