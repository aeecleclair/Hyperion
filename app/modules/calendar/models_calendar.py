from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.core_endpoints.models_core import CoreUser
from app.modules.calendar.types_calendar import CalendarEventType
from app.types.sqlalchemy import Base


class Event(Base):
    """Events for calendar."""

    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    name: Mapped[str]
    organizer: Mapped[str]
    applicant_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    start: Mapped[datetime]
    end: Mapped[datetime]
    all_day: Mapped[bool]
    location: Mapped[str]
    type: Mapped[CalendarEventType]
    description: Mapped[str]
    decision: Mapped[str]
    recurrence_rule: Mapped[str | None]

    applicant: Mapped[CoreUser] = relationship("CoreUser", init=False)
