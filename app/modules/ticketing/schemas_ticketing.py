from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.core.myeclpay.schemas_myeclpay import StoreSimple


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
    store: "StoreSimple"
    sessions: list["SessionComplete"]
    categories: list["CategoryComplete"]


class EventUpdate(BaseModel):
    name: str | None = None
    open_date: datetime | None = None
    close_date: datetime | None = None
    quota: int | None = None
    user_quota: int | None = None
    disabled: bool | None = None


class SessionBase(BaseModel):
    name: str
    quota: int | None = None
    user_quota: int | None = None


class SessionComplete(SessionBase):
    id: UUID
    used_quota: int
    disabled: bool


class SessionUpdate(BaseModel):
    name: str | None = None
    quota: int | None = None
    user_quota: int | None = None
    disabled: bool | None = None


class CategoryBase(BaseModel):
    event_id: UUID
    name: str
    linked_sessions: list[UUID] | None = None
    required_mebership: UUID | None = None
    quota: int | None = None
    user_quota: int | None = None
    price: int


class CategoryComplete(CategoryBase):
    id: UUID
    used_quota: int
    disabled: bool


class CategoryUpdate(BaseModel):
    name: str | None = None
    linked_sessions: list[UUID] | None = None
    required_mebership: UUID | None = None
    quota: int | None = None
    user_quota: int | None = None
    price: int | None = None
    disabled: bool | None = None


class TicketBase(BaseModel):
    user_id: str
    event_id: UUID
    category_id: UUID
    total: int


class TicketSimple(TicketBase):
    id: UUID
    created_at: datetime


class TicketComplete(TicketSimple):
    event: EventComplete
    category: CategoryComplete
