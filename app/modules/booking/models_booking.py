"""model file for booking"""

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.core.core_endpoints.models_core import CoreUser

from app.modules.booking.types_booking import Decision
from app.types.sqlalchemy import Base


class Manager(Base):
    __tablename__ = "booking_manager"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"))
    rooms: Mapped[list["Room"]] = relationship(
        back_populates="manager",
        default_factory=list,
    )


class Room(Base):
    __tablename__ = "booking_room"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    manager_id: Mapped[str] = mapped_column(
        ForeignKey("booking_manager.id"),
    )
    manager: Mapped["Manager"] = relationship(
        lazy="joined",
        back_populates="rooms",
        init=False,
    )
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="room",
        default_factory=list,
    )


class Booking(Base):
    __tablename__ = "booking"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    reason: Mapped[str]
    start: Mapped[datetime]
    end: Mapped[datetime]
    creation: Mapped[datetime]
    note: Mapped[str | None]
    room_id: Mapped[str] = mapped_column(
        ForeignKey("booking_room.id"),
        index=True,
    )
    key: Mapped[bool]
    decision: Mapped[Decision]
    recurrence_rule: Mapped[str | None]
    applicant_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    entity: Mapped[str]

    applicant: Mapped[CoreUser] = relationship("CoreUser", init=False)
    room: Mapped[Room] = relationship(
        lazy="joined",
        back_populates="bookings",
        init=False,
    )
