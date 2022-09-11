from datetime import datetime

from pydantic import BaseModel

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

    class Config:
        orm_mode = True


class EventComplete(EventBase):
    id: str
