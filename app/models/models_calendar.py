from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.models_core import CoreUser
from app.utils.types.calendar_types import CalendarEventType


class Event(Base):
    event_id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, nullable=False)
    organizer: str = Column(String, nullable=False)
    supervisor: CoreUser = relationship(
        "CoreUser",
    )
    start: datetime = Column(DateTime, nullable=False)
    end: datetime = Column(DateTime, nullable=False)
    place: str = Column(String)
    type: CalendarEventType = Column(
        Enum(CalendarEventType),
        nullable=False,
    )
    description: str = Column(String, nullable=False)
    recurrence: bool = Column(Boolean, nullable=False)
    recurrence_end_date: datetime = Column(DateTime)
    recurrence_rule: str = Column(String)
