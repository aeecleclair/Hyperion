from datetime import datetime

from pydantic import BaseModel

from app.utils.types.calendar_types import CalendarEventType


# Schema de base. Contiens toutes les données communes à tous les schemas
class EventBase(BaseModel):
    name: str
    organizer: str
    start: datetime
    end: datetime
    place: str
    type: CalendarEventType
    description: str
    recurrence: bool
    recurrence_end_date: datetime | None
    recurrence_rule: str | None

    class Config:
        orm_mode = True


class EventComplete(EventBase):
    id: str
