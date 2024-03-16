from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models_core import CoreUser
from app.database import Base
from app.modules.calendar.types_calendar import CalendarEventType
from app.utils.types.datetime import TZDateTime


class Event(Base):
    """Events for calendar."""

    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    organizer: Mapped[str] = mapped_column(String, nullable=False)
    applicant_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        nullable=False,
    )
    applicant: Mapped[CoreUser] = relationship("CoreUser")
    start: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    end: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[CalendarEventType] = mapped_column(
        Enum(CalendarEventType),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    recurrence_rule: Mapped[str | None] = mapped_column(String)
