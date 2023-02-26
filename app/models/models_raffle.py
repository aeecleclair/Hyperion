"""Models file for module_tombola"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.database import Base


class Raffle(Base):
    __tablename__ = "raffle"
    id: str = Column(String, primary_key=True, index=True, nullable=False)
    name: str = Column(String, nullable=False)
    start_date: datetime = Column(DateTime, nullable=False)
    end_date: datetime = Column(DateTime, nullable=False)
    group_id: str = Column(String, index=True, nullable=False)
    description: str = Column(String, index=True, nullable=True)


class TypeTicket(Base):
    __tablename__ = "type_ticket"
    price: float = Column(Float, nullable=False)
    id: str = Column(String, primary_key=True, index=True, nullable=False)
    nb_ticket: int = Column(Integer)
    raffle_id: str = Column(ForeignKey("raffle.id"), index=True, nullable=False)


class Lots(Base):
    __tablename__ = "lots"

    id: str = Column(String, primary_key=True, index=True, nullable=False)
    raffle_id: str = Column(ForeignKey("raffle.id"), index=True, nullable=False)
    description: str = Column(String, nullable=True)
    quantity: int = Column(Integer)


class Tickets(Base):
    __tablename__ = "tickets"

    id: str = Column(String, primary_key=True, index=True, nullable=False)
    type_id: str = Column(ForeignKey("type_ticket.id"), nullable=False)
    user_id: str = Column(Integer, nullable=False)  # --> Récupérer sur hyperion
    winning_lot: str = Column(String, nullable=True, index=True)
