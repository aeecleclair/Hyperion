from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.core.associations.schemas_associations import Association
from app.modules.calendar.types_calendar import Decision


# Schema de base. Contiens toutes les données communes à tous les schemas
class EventBase(BaseModel):
    name: str
    start: datetime
    end: datetime
    all_day: bool
    location: str
    description: str | None = None
    recurrence_rule: str | None = None

    ticket_url_opening: datetime | None = None

    notification: bool

    association_id: UUID


class EventBaseCreation(EventBase):
    ticket_url: str | None = None

    @model_validator(mode="after")
    def check_ticket(self):
        if (self.ticket_url_opening and not self.ticket_url) or (
            self.ticket_url and not self.ticket_url_opening
        ):
            raise ValueError

        return self


class EventComplete(EventBase):
    id: UUID
    association: Association
    decision: Decision


class EventCompleteTicketUrl(EventComplete):
    ticket_url: str | None = None


class EventTicketUrl(BaseModel):
    ticket_url: str


class EventEdit(BaseModel):
    name: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    all_day: bool | None = None
    location: str | None = None
    description: str | None = None
    recurrence_rule: str | None = None
    ticket_url_opening: datetime | None = None
    ticket_url: str | None = None
    notification: bool | None = None


class IcalSecret(BaseModel):
    secret: str
