from datetime import datetime

from pydantic import BaseModel, validator

from app.schemas.schemas_core import CoreUserSimple
from app.utils import validators
from app.utils.types.calendar_types import CalendarEventType, Decision


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

    _normalize_start = validator("start", allow_reuse=True)(
        validators.time_zone_converter
    )
    _normalize_end = validator("end", allow_reuse=True)(validators.time_zone_converter)


class EventComplete(EventBase):
    id: str
    decision: Decision
    applicant_id: str

    class Config:
        orm_mode = True


class EventEdit(BaseModel):
    name: str | None = None
    organizer: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    all_day: bool | None = None
    location: str | None = None
    type: CalendarEventType | None = None
    description: str | None = None
    recurrence_rule: str | None = None

    _normalize_start = validator("start", allow_reuse=True)(
        validators.time_zone_converter
    )
    _normalize_end = validator("end", allow_reuse=True)(validators.time_zone_converter)

    class Config:
        orm_mode = True


class EventApplicant(CoreUserSimple):
    email: str
    promo: int | None = None
    phone: str | None = None


class EventReturn(EventComplete):
    applicant: EventApplicant

    class Config:
        orm_mode = True
