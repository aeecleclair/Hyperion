from uuid import UUID

from pydantic import BaseModel

from app.core.users.schemas_users import CoreUserSimple
from app.modules.calendar.types_calendar import Decision, QuestionType


# Schema de base. Contiens toutes les données communes à tous les schemas
class EventBase(BaseModel):
    name: str
    applicant: CoreUserSimple
    applicant_id: str
    form_id: UUID


class EventComplete(EventBase):
    id: str
    decision: Decision


class EventEdit(BaseModel):
    name: str | None = None


class EventApplicant(CoreUserSimple):
    email: str
    promo: int | None = None
    phone: str | None = None


class EventReturn(EventComplete):
    applicant: EventApplicant


class QuestionBase(BaseModel):
    text: str
    question_type: QuestionType
    yes_question_list: list[UUID]
    no_question_list: list[UUID]
    form_id: UUID


class QuestionComplete(QuestionBase):
    id: UUID


class QuestionEdit(BaseModel):
    text: str | None = None
    question_type: QuestionType | None = None


class ContactBase(BaseModel):
    mail: str
    question_id: UUID


class ContactComplete(ContactBase):
    id: UUID


class ContactEdit(BaseModel):
    mail: str | None = None


class ConfirmationChainsBase(BaseModel):
    number: int
    confirming_body_id: UUID
    form_id: UUID


class ConfirmationChainsComplete(ConfirmationChainsBase):
    id: UUID


class ConfirmationChainsEdit(BaseModel):
    confirming_body_id: UUID | None = None
    number: int | None = None


class ReponseBase(BaseModel):
    text: str
    question_id: UUID
    event_id: UUID


class ReponseComplete(ReponseBase):
    id: UUID


class ReponseEdit(BaseModel):
    text: str | None = None


class FormBase(BaseModel):
    name: str

class FormComplete(FormBase):
    id: UUID


class FormEdit(BaseModel):
    name: str | None = None 


class ConfirmationEventsBase(BaseModel):
    state: Decision
    event_id: UUID
    confirming_body_id: UUID


class ConfirmationEventsComplete(ConfirmationEventsBase):
    id: UUID
    number: int




