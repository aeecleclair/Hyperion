from datetime import datetime
from pydantic import BaseModel


class Booking(BaseModel):
    """The booking schema is a request on the client side"""

    booker: str
    room: str
    start: datetime
    end: datetime
    reason: str = None
    notes: str = None
    key: bool
    multiple_days: bool
    recurring: bool


class BookingRequest(Booking):
    """The BookingRequest schema is a request on the server side"""

    pending: bool = True

    class Config:
        orm_mode = True
