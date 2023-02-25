"""Models file for module_tombola"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.database import Base


class Raffle(Base):
    __tablename__ = "raffle"
    id: str = Column(String, primary_key=True, index=True)
    raffle_name: str = Column(String)
    start_date: datetime = Column(DateTime, nullable=False)
    end_date: datetime = Column(DateTime, nullable=False)
    group_id: int = Column(Integer)
    rules: str = Column(String, index=True)


class TypeTicket(Base):
    __tablename__ = "type_ticket"

    id: str = Column(String, primary_key=True, index=True)
    raffle_id: int = Column(ForeignKey("raffle.id"))
    rate: float = Column(Float)
    nb_ticket: int = Column(Integer)


class Lots(Base):
    __tablename__ = "lots"

    id: str = Column(String, primary_key=True, index=True)
    raffle_id: int = Column(ForeignKey("raffle.id"))
    description: str = Column(String)


class Tickets(Base):
    __tablename__ = "tickets"

    id: str = Column(String, primary_key=True, index=True)
    type_id: int = Column(ForeignKey("type_ticket.id"))
    # player_id: string --> Récupérer sur hyperion
    lot_gagnant: int = Column(Integer, nullable=True)
