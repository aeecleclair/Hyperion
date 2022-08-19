"""model file for bdebooking"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String

from app.database import Base


class Booking(Base):
    __tablename__ = "bde_booking"
    url: str = Column(String, nullable=False)
    id: str = Column(String, primary_key=True, index=True)
    reason: str = Column(String, nullable=False)
    start: datetime = Column(DateTime, nullable=False)
    end: datetime = Column(DateTime, nullable=False)
    note: str = Column(String, nullable=True)
    room: str = Column(String, nullable=False, index=True)
    key: bool = Column(Boolean, nullable=False)
    confirmed: bool = Column(Boolean, nullable=False)  # If BDE made a decision
    authorized: bool = Column(Boolean, nullable=False)  # BDE's decision
    multipleDay: bool = Column(Boolean, nullable=False)
    recurring: bool = Column(Boolean, nullable=False)
    applicant_id: str = Column(ForeignKey("core_user.id"), nullable=False)
