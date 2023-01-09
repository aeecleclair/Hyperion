"""Schemas file for endpoint /bdebooking"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple
from app.utils.types.bdebooking_type import Decision


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
    reason: str
    start: datetime
    end: datetime
    note: str | None
    room_id: str
    key: bool
    recurrence_rule: str | None = None
    entity: str


class BookingComplete(BookingBase):
    id: str
    decision: Decision
    applicant_id: str


class Applicant(CoreUserSimple):
    email: str
    promo: int | None = None
    phone: str | None = None


class BookingReturn(BookingComplete):
    room: RoomComplete

    class Config:
        orm_mode = True


class BookingReturnApplicant(BookingReturn):
    applicant: Applicant


class BookingEdit(BaseModel):
    reason: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    note: str | None = None
    room: str | None = None
    key: bool | None = None
    recurrence_rule: str | None = None
    entity: str | None = None
