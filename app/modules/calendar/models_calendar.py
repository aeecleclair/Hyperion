from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.users.models_users import CoreUser
from app.modules.calendar.types_calendar import Decision, Question_type
from app.types.sqlalchemy import Base, PrimaryKey


class Event(Base):
    """Events for calendar."""

    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    name: Mapped[str]
    applicant_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    form_id: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_forms.id"),
    )

    applicant: Mapped[CoreUser] = relationship("CoreUser", init=False)


class Question(Base):
    """Questions in forms."""

    __tablename__ = "calendar_questions_forms"

    id: Mapped[PrimaryKey]
    text: Mapped[str]
    next_question_yes: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_questions_forms.id"),
    )
    next_question_no: Mapped[UUID | None] = mapped_column(
        ForeignKey("calendar_questions_forms.id"),
    )
    form_id: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_forms.id"),
    )
    question_type: Mapped[Question_type]


class Response(Base):
    """Responses to questions."""

    __tablename__ = "calendar_responses"

    id: Mapped[PrimaryKey]
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_questions_forms.id"),
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_events.id"),
    )
    text: Mapped[str]


class Form(Base):
    """Forms."""

    __tablename__ = "calendar_forms"

    id: Mapped[PrimaryKey]
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_events.id"),
    )


class Contact(Base):
    """People to contact."""

    __tablename__ = "calendar_contacts"

    id: Mapped[PrimaryKey]
    mail: Mapped[str]
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_questions_forms.id"),
    )


class ConfirmationChains(Base):
    """People who need to confirm."""

    __tablename__ = "calendar_confirmation_chains"

    id: Mapped[PrimaryKey]
    number: Mapped[int]
    form_id: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_forms.id"),
    )
    confirming_body_id: Mapped[UUID] = mapped_column(
        ForeignKey("core_groups.id"),
    )


class ConfirmationEvents(Base):
    """State of events."""

    __tablename__ = "calendar_confirmation_events"

    id: Mapped[PrimaryKey]
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_events.id"),
    )
    confirming_body_id: Mapped[UUID] = mapped_column(
        ForeignKey("core_groups.id"),
    )
    state: Mapped[Decision]
