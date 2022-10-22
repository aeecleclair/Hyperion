from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, String

from app.database import Base
from app.utils.types.calendar_types import CalendarEventType


class Event(Base):
    """Events for calendar."""

    __tablename__ = "calendar_events"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, nullable=False)
    organizer: str = Column(String, nullable=False)
    start: datetime = Column(DateTime, nullable=False)
    end: datetime = Column(DateTime, nullable=False)
    all_day: bool = Column(Boolean, nullable=False)
    location: str = Column(String, nullable=False)
    type: CalendarEventType = Column(
        Enum(CalendarEventType),
        nullable=False,
    )
    description: str = Column(String, nullable=False)
    recurrence_rule: str | None = Column(String)
