from datetime import datetime

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple
from app.utils.types.bdebooking_type import Decision
from app.utils.types.calendar_types import CalendarEventType


# Schema de base. Contiens toutes les données communes à tous les schemas
class EventBase(BaseModel):
    name: str
    organizer: str
    start: datetime
    end: datetime
    all_day: bool
    location: str
    type: CalendarEventType
    description: str
    recurrence_rule: str | None
    applicant_id: str


class EventComplete(EventBase):
    id: str
    decision: Decision


class Applicant(CoreUserSimple):
    email: str
    promo: int | None = None
    phone: str | None = None


class EventReturn(EventComplete):
    applicant: Applicant

    class Config:
        orm_mode = True
