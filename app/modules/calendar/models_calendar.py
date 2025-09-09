from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.associations.models_associations import CoreAssociation
from app.modules.calendar.types_calendar import Decision
from app.types.sqlalchemy import Base, PrimaryKey


class Event(Base):
    """Events for calendar."""

    __tablename__ = "calendar_events"

    id: Mapped[PrimaryKey]
    name: Mapped[str]

    association_id: Mapped[UUID] = mapped_column(
        ForeignKey("associations_associations.id"),
    )
    applicant_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )

    start: Mapped[datetime]
    end: Mapped[datetime]
    all_day: Mapped[bool]
    location: Mapped[str]
    description: Mapped[str | None]
    decision: Mapped[Decision]
    recurrence_rule: Mapped[str | None]

    ticket_url: Mapped[str | None]
    ticket_url_opening: Mapped[datetime | None]
    notification: Mapped[bool]

    association: Mapped[CoreAssociation] = relationship("CoreAssociation", init=False)


class IcalSecret(Base):
    __tablename__ = "calendar_ical_secret"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    secret: Mapped[str]
