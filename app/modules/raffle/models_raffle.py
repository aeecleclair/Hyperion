"""Models file for module_tombola"""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.core_endpoints.schemas_core import CoreUser
from app.core.groups.models_groups import CoreGroup
from app.modules.raffle.types_raffle import RaffleStatusType
from app.types.sqlalchemy import Base


class Raffle(Base):
    __tablename__ = "raffle"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    name: Mapped[str]

    group_id: Mapped[str] = mapped_column(
        ForeignKey("core_group.id"),
        index=True,
    )
    description: Mapped[str | None] = mapped_column(index=True)

    status: Mapped[RaffleStatusType] = mapped_column(
        default=RaffleStatusType.creation,
    )

    group: Mapped[CoreGroup] = relationship("CoreGroup", init=False)


class PackTicket(Base):
    __tablename__ = "raffle_pack_ticket"
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    price: Mapped[float]
    pack_size: Mapped[int]
    raffle_id: Mapped[str] = mapped_column(
        ForeignKey("raffle.id"),
        index=True,
    )

    raffle: Mapped[Raffle] = relationship("Raffle", init=False)


class Prize(Base):
    __tablename__ = "raffle_prize"

    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    raffle_id: Mapped[str] = mapped_column(
        ForeignKey("raffle.id"),
        index=True,
    )
    description: Mapped[str | None]
    name: Mapped[str | None]
    quantity: Mapped[int]

    raffle: Mapped[Raffle] = relationship("Raffle", init=False)


class Ticket(Base):
    __tablename__ = "raffle_ticket"

    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    pack_id: Mapped[str] = mapped_column(
        ForeignKey("raffle_pack_ticket.id"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    winning_prize: Mapped[str | None] = mapped_column(
        ForeignKey("raffle_prize.id"),
        index=True,
        default=None,
    )

    pack_ticket: Mapped[PackTicket] = relationship("PackTicket", init=False)
    prize: Mapped[Prize | None] = relationship("Prize", init=False)
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)


class Cash(Base):
    __tablename__ = "raffle_cash"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    balance: Mapped[float]

    user: Mapped[CoreUser] = relationship("CoreUser", init=False)
