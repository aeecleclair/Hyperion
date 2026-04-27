from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrganiserBase(BaseModel):
    name: str


class OrganiserComplete(OrganiserBase):
    id: UUID
    store_id: UUID

    model_config = ConfigDict(from_attributes=True)


class OrganiserEdit(BaseModel):
    name: str | None = None
    store_id: UUID | None = None


class EventBase(BaseModel):
    organiser_id: UUID
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

    model_config = ConfigDict(from_attributes=True)


class EventComplete(EventSimple):
    organiser: "OrganiserComplete"
    sessions: list["SessionSimple"]
    categories: list["CategorySimple"]

    model_config = ConfigDict(from_attributes=True)


class EventUpdate(BaseModel):
    name: str | None = None
    open_date: datetime | None = None
    close_date: datetime | None = None
    quota: int | None = None
    user_quota: int | None = None
    disabled: bool | None = None


class SessionBase(BaseModel):
    event_id: UUID
    date: datetime
    name: str
    quota: Annotated[int, Field(gt=0)] | None = None
    user_quota: Annotated[int, Field(gt=0)] | None = None


class SessionSimple(SessionBase):
    id: UUID
    used_quota: int
    disabled: bool

    model_config = ConfigDict(from_attributes=True)


class SessionComplete(SessionSimple):
    event: EventSimple

    model_config = ConfigDict(from_attributes=True)


class SessionUpdate(BaseModel):
    name: str | None = None
    quota: Annotated[int, Field(gt=0)] | None = None
    user_quota: Annotated[int, Field(gt=0)] | None = None
    disabled: bool | None = None


class CategoryBase(BaseModel):
    event_id: UUID
    name: str
    required_mebership: UUID | None = None
    quota: Annotated[int, Field(gt=0)] | None = None
    user_quota: Annotated[int, Field(gt=0)] | None = None
    price: Annotated[int, Field(gt=0)]


class CategoryCreate(CategoryBase):
    sessions: list[UUID] | None = None


class CategorySimple(CategoryBase):
    id: UUID
    used_quota: int
    disabled: bool

    model_config = ConfigDict(from_attributes=True)


class CategoryComplete(CategorySimple):
    event: EventSimple
    sessions: list[UUID] | None = None

    model_config = ConfigDict(from_attributes=True)


class CategoryUpdate(BaseModel):
    name: str | None = None
    sessions: list[UUID] | None = None
    required_mebership: UUID | None = None
    quota: Annotated[int, Field(gt=0)] | None = None
    user_quota: Annotated[int, Field(gt=0)] | None = None
    price: Annotated[int, Field(gt=0)] | None = None
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

    model_config = ConfigDict(from_attributes=True)


class TicketComplete(TicketSimple):
    event: EventSimple
    category: CategorySimple
    session: SessionSimple | None

    model_config = ConfigDict(from_attributes=True)
