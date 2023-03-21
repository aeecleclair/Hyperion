"""Models file for module_tombola"""
from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.models_core import CoreUser
from app.utils.types.raffle_types import RaffleStatusType


class Raffle(Base):
    __tablename__ = "raffle"
    id: str = Column(String, primary_key=True, index=True, nullable=False)
    name: str = Column(String, nullable=False)
    status: RaffleStatusType = Column(
        Enum(RaffleStatusType), nullable=False, default=RaffleStatusType.creation
    )
    group_id: str = Column(ForeignKey("core_group.id"), index=True, nullable=False)
    description: str = Column(String, index=True, nullable=True)


class TypeTicket(Base):
    __tablename__ = "raffle_type_ticket"
    id: str = Column(String, primary_key=True, index=True, nullable=False)
    price: float = Column(Float, nullable=False)
    nb_ticket: int = Column(Integer)
    raffle_id: str = Column(ForeignKey("raffle.id"), index=True, nullable=False)


class Lots(Base):
    __tablename__ = "raffle_lots"

    id: str = Column(String, primary_key=True, index=True, nullable=False)
    raffle_id: str = Column(ForeignKey("raffle.id"), index=True, nullable=False)
    description: str = Column(String, nullable=True)
    name: str = Column(String, nullable=True)
    quantity: int = Column(Integer)


class Tickets(Base):
    __tablename__ = "raffle_tickets"

    id: str = Column(String, primary_key=True, index=True, nullable=False)
    raffle_id: str = Column(ForeignKey("raffle.id"), index=True, nullable=False)
    type_id: str = Column(ForeignKey("raffle_type_ticket.id"), nullable=False)
    user_id: str = Column(ForeignKey("raffle_cash.user_id"), nullable=False)
    unit_price: float = Column(Float, nullable=False)
    nb_tickets: int = Column(Integer, nullable=False)
    group_id: str = Column(ForeignKey("core_group.id"), index=True, nullable=False)
    winning_lot: str = Column(String, nullable=True, index=True)


class Cash(Base):
    __tablename__ = "raffle_cash"

    user_id: str = Column(String, ForeignKey("core_user.id"), primary_key=True)
    user: CoreUser = relationship("CoreUser")
    balance: float = Column(Float, nullable=False)
