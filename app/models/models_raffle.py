"""Models file for module_tombola"""
from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.models_core import CoreGroup, CoreUser
from app.utils.types.raffle_types import RaffleStatusType


class Raffle(Base):
    __tablename__ = "raffle"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[RaffleStatusType] = mapped_column(
        Enum(RaffleStatusType), nullable=False, default=RaffleStatusType.creation
    )
    group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String, index=True, nullable=True)

    group: CoreGroup = relationship("CoreGroup")


class PackTicket(Base):
    __tablename__ = "raffle_pack_ticket"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    pack_size: Mapped[int] = mapped_column(Integer, nullable=False)
    raffle_id: Mapped[str] = mapped_column(
        ForeignKey("raffle.id"), index=True, nullable=False
    )

    raffle: Mapped[Raffle] = relationship("Raffle")


class Lots(Base):
    __tablename__ = "raffle_lots"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    raffle_id: Mapped[str] = mapped_column(
        ForeignKey("raffle.id"), index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)

    raffle: Mapped[Raffle] = relationship("Raffle")


class Tickets(Base):
    __tablename__ = "raffle_tickets"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False
    )
    type_id: Mapped[str] = mapped_column(
        ForeignKey("raffle_pack_ticket.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), nullable=False)
    winning_lot: Mapped[str] = mapped_column(
        ForeignKey("raffle_lots.id"), nullable=True, index=True
    )

    pack_ticket: Mapped[PackTicket] = relationship("PackTicket")
    lot: Mapped[Lots | None] = relationship("Lots")
    user: Mapped[CoreUser] = relationship("CoreUser")


class Cash(Base):
    __tablename__ = "raffle_cash"

    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("core_user.id"), primary_key=True
    )
    balance: Mapped[float] = mapped_column(Float, nullable=False)

    user: Mapped[CoreUser] = relationship("CoreUser")
