from datetime import datetime

from pydantic import BaseModel

from app.models.models_core import CoreUser
from app.utils.types.calendar_types import CalendarEventType


# Schema de base. Contiens toutes les données communes à tous les schemas
class EventBase(BaseModel):
    event_id: str
    name: str
    organizer: str
    supervisor: CoreUser | None
    start: datetime
    end: datetime
    place: str
    type: CalendarEventType
    description: str
    recurrence: bool
    recurrence_end_date: datetime | None
    recurrence_rule: str | None


# Format des données présente dans la base de donnée
class TodosItemInDB(EventBase):
    todo_id: str
    creation_time: datetime
