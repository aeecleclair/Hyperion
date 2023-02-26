"""Models file for module_tombola"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.database import Base


class Raffle(Base):
    __tablename__ = "raffle"
    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String)
    start_date: datetime = Column(DateTime, nullable=False)
    end_date: datetime = Column(DateTime, nullable=False)
    group_id: str = Column(String, index=True)
    description: str = Column(String, index=True)


class TypeTicket(Base):
    __tablename__ = "type_ticket"
    price: float = Column(Float)
    id: str = Column(String, primary_key=True, index=True)
    nb_ticket: int = Column(Integer)
    raffle_id: str = Column(ForeignKey("raffle.id"), index=True)


class Lots(Base):
    __tablename__ = "lots"

    id: str = Column(String, primary_key=True, index=True)
    raffle_id: str = Column(ForeignKey("raffle.id"), index=True)
    description: str = Column(String)
    quantity: int = Column(Integer)


class Tickets(Base):
    __tablename__ = "tickets"

    id: str = Column(String, primary_key=True, index=True)
    type_id: str = Column(ForeignKey("type_ticket.id"))
    # user_id: string --> Récupérer sur hyperion
    winning_lot: str = Column(String, nullable=True, index=True)
