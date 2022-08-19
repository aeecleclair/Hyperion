"""Schemas file for endpoint /bdebooking"""

from datetime import datetime

from pydantic import BaseModel


class Rights(BaseModel):
    view: bool
    manage: bool


class RoomBase(BaseModel):
    name: str


class RoomComplete(RoomBase):
    id: str

    class Config:
        orm_mode = True


class BookingBase(BaseModel):
    url: str
    reason: str
    start: datetime
    end: datetime
    note: str
    room_id: str
    key: bool
    multipleDay: bool
    recurring: bool


class BookingComplete(BookingBase):
    id: str
    confirmed: bool
    authorized: bool


class BookingReturn(BookingComplete):
    room: RoomComplete

    class Config:
        orm_mode = True


class BookingEdit(BaseModel):
    url: str | None = None
    reason: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    note: str | None = None
    room: str | None = None
    key: bool | None = None
    multipleDay: bool | None = None
    recurring: bool | None = None
    id: str
