"""Schemas file for endpoint /bdebooking"""

from datetime import datetime

from pydantic import BaseModel


class BookingBase(BaseModel):
    url: str
    reason: str
    start: datetime
    end: datetime
    note: str
    room: str
    key: bool
    multipleDay: bool
    recurring: bool


class BookingComplete(BookingBase):
    id: str
    confirmed: bool

    class Config:
        orm_mode = True
