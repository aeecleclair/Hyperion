from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.models_core import CoreUser
from app.utils.types.calendar_types import CalendarEventType


class Event(Base):
    """Events for calendar."""

    __tablename__ = "calendar_events"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, nullable=False)
    organizer: str = Column(String, nullable=False)
    applicant_id: str = Column(ForeignKey("core_user.id"), nullable=False)
    applicant: CoreUser = relationship("CoreUser")
    start: datetime = Column(DateTime(timezone=True), nullable=False)
    end: datetime = Column(DateTime(timezone=True), nullable=False)
    all_day: bool = Column(Boolean, nullable=False)
    location: str = Column(String, nullable=False)
    type: CalendarEventType = Column(
        Enum(CalendarEventType),
        nullable=False,
    )
    description: str = Column(String, nullable=False)
    decision: str = Column(String, nullable=False)
    recurrence_rule: str | None = Column(String)
