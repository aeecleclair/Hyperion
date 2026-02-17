from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.mypayment.schemas_mypayment import StoreSimple


class EventBase(BaseModel):
    store_id: UUID
    name: str
    open_date: datetime
    close_date: datetime | None = None
    quota: int | None = None
    user_quota: int | None = None


class EventSimple(EventBase):
    creator_id: str
    id: UUID
    used_quota: int
    disabled: bool


class EventComplete(EventSimple):
    store: StoreSimple
    sessions: list["SessionSimple"]
    categories: list["CategorySimple"]


class EventUpdate(BaseModel):
    name: str | None = None
    open_date: datetime | None = None
    close_date: datetime | None = None
    quota: int | None = None
    user_quota: int | None = None
    disabled: bool | None = None


class SessionBase(BaseModel):
    event_id: UUID
    name: str
    quota: int | None = None
    user_quota: int | None = None


class SessionSimple(SessionBase):
    id: UUID
    used_quota: int
    disabled: bool


class SessionComplete(SessionSimple):
    event: EventSimple


class SessionUpdate(BaseModel):
    name: str | None = None
    quota: int | None = None
    user_quota: int | None = None
    disabled: bool | None = None


class CategoryBase(BaseModel):
    event_id: UUID
    name: str
    required_mebership: UUID | None = None
    quota: int | None = None
    user_quota: int | None = None
    price: int


class CategorySimple(CategoryBase):
    id: UUID
    used_quota: int
    disabled: bool


class CategoryComplete(CategorySimple):
    event: EventSimple
    sessions: list[UUID] | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    sessions: list[UUID] | None = None
    required_mebership: UUID | None = None
    quota: int | None = None
    user_quota: int | None = None
    price: int | None = None
    disabled: bool | None = None


class TicketBase(BaseModel):
    user_id: str
    event_id: UUID
    category_id: UUID
    session_id: UUID
    total: int


class TicketSimple(TicketBase):
    id: UUID
    created_at: datetime
    status: str
    nb_scan: int


class TicketComplete(TicketSimple):
    event: EventComplete
    category: CategoryComplete
    session: SessionComplete
