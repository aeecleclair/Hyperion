from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.types.sqlalchemy import Base, PrimaryKey

if TYPE_CHECKING:
    from app.core.myeclpay.models_myeclpay import Store


class Event(Base):
    __tablename__ = "ticketing_event"

    id: Mapped[PrimaryKey]
    store_id: Mapped[UUID] = mapped_column(ForeignKey("myeclpay_store.id"))
    store: Mapped["Store"] = relationship(
        init=False,
        lazy="selectin",
    )
    creator_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    name: Mapped[str]
    open_date: Mapped[datetime]
    close_date: Mapped[datetime | None]
    quota: Mapped[int | None]
    used_quota: Mapped[int]
    user_quota: Mapped[int | None]
    disabled: Mapped[bool]

    sessions: Mapped[list["Session"]] = relationship(
        init=False,
        lazy="selectin",
    )
    categories: Mapped[list["Category"]] = relationship(
        init=False,
        lazy="selectin",
    )


class Session(Base):
    __tablename__ = "ticketing_session"

    id: Mapped[PrimaryKey]
    event_id: Mapped[UUID] = mapped_column(ForeignKey("ticketing_event.id"))
    event: Mapped[Event] = relationship(
        init=False,
        lazy="selectin",
    )
    name: Mapped[str]
    quota: Mapped[int | None]
    used_quota: Mapped[int]
    user_quota: Mapped[int | None]
    disabled: Mapped[bool]


class Category(Base):
    __tablename__ = "ticketing_category"

    id: Mapped[PrimaryKey]
    event_id: Mapped[UUID] = mapped_column(ForeignKey("ticketing_event.id"))
    event: Mapped[Event] = relationship(
        init=False,
        lazy="selectin",
    )
    name: Mapped[str]
    linked_sessions: Mapped[list[UUID] | None]
    required_mebership: Mapped[UUID | None] = mapped_column(
        ForeignKey("core_association_membership.id"),
    )
    quota: Mapped[int | None]
    used_quota: Mapped[int]
    user_quota: Mapped[int | None]
    price: Mapped[int]
    disabled: Mapped[bool]


class Ticket(Base):
    __tablename__ = "ticketing_ticket"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    event_id: Mapped[UUID] = mapped_column(ForeignKey("ticketing_event.id"))
    event: Mapped[Event] = relationship(
        init=False,
        lazy="selectin",
    )
    category_id: Mapped[UUID] = mapped_column(ForeignKey("ticketing_category.id"))
    category: Mapped[Category] = relationship(
        init=False,
        lazy="selectin",
    )
    total: Mapped[int]
    created_at: Mapped[datetime]
    status: Mapped[str]
    nb_scan: Mapped[int]
