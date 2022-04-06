from datetime import datetime
from pydantic import BaseModel


class Booking(BaseModel):  #

    booker: str
    room: str
    start: datetime
    end: datetime
    reason: str = None
    notes: str = None
    key: bool
    pending: bool
    multiple_days: bool
    recurring: bool

    class Config:
        orm_mode = True
