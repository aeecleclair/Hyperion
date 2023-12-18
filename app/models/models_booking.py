"""model file for booking"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.models_core import CoreUser


class Manager(Base):
    __tablename__ = "booking_manager"

    id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"), nullable=False)
    rooms: Mapped[list["Room"]] = relationship(back_populates="manager")


class Room(Base):
    __tablename__ = "booking_room"

    id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    manager_id: Mapped[str] = mapped_column(
        ForeignKey("booking_manager.id"), nullable=False
    )
    manager: Mapped["Manager"] = relationship(lazy="joined", back_populates="rooms")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="room")


class Booking(Base):
    __tablename__ = "booking"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    creation: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str] = mapped_column(String, nullable=True)
    room_id: Mapped[str] = mapped_column(
        ForeignKey("booking_room.id"), nullable=False, index=True
    )
    room: Mapped[Room] = relationship(Room, lazy="joined", back_populates="bookings")
    key: Mapped[bool] = mapped_column(Boolean, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    recurrence_rule: Mapped[str | None] = mapped_column(String)
    applicant_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"), nullable=False
    )
    applicant: Mapped[CoreUser] = relationship("CoreUser")
    entity: Mapped[str] = mapped_column(String)
