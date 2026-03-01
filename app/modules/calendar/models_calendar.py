from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.users.models_users import CoreUser
from app.modules.calendar.types_calendar import Decision, QuestionType
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
    
    no_question_list: Mapped[UUID] = mapped_column(list,
        ForeignKey("calendar_questions_forms.id"),
    )
    yes_question_list: Mapped[UUID] = mapped_column(list,
        ForeignKey("calendar_questions_forms.id"),
    )
    form_id: Mapped[UUID] = mapped_column(
        ForeignKey("calendar_forms.id"),
    )
    question_type: Mapped[QuestionType]


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

    name: Mapped[str]
    id: Mapped[PrimaryKey]


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
        ForeignKey("calendar_confirmation_chains.conforming_body_id"),
        primary_key=True,
    )
    number: Mapped[int] = mapped_column(
        ForeignKey("calendar_confirmation_chains.number"),
        primary_key=True,
    )
    state: Mapped[Decision]
