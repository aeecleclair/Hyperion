import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.core.models_core import CoreUser

from app.types.sqlalchemy import Base, PrimaryKey


class TicketGenerator(Base):
    __tablename__ = "ticket_generator"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    max_use: Mapped[int]
    expiration: Mapped[datetime]
    scanner_group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"))


class Ticket(Base):
    __tablename__ = "ticket"
    id: Mapped[PrimaryKey]
    secret: Mapped[uuid.UUID] = mapped_column(unique=True)
    generator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_generator.id"),
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    name: Mapped[str]
    user: Mapped["CoreUser"] = relationship("CoreUser")
    scan_left: Mapped[int]
    tags: Mapped[str]  # Comma separated values
    expiration: Mapped[datetime]
