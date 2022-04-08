from sqlalchemy import Column, Integer, Boolean, DateTime, VARCHAR, TEXT, ForeignKey
from ..database import Base


class RoomBooking(Base):
    __tablename__ = "room_booking"

    id = Column(Integer, primary_key=True, index=True)  # Use UUID later
    booker = Column(
        VARCHAR, nullable=False
    )  # the id of the user in the table CoreUser (require authentification)
    room = Column(VARCHAR, nullable=False)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    reason = Column(TEXT)  # Reason of the booking
    notes = Column(TEXT)  # Allow booker to precise the reason of the booking
    key = Column(Boolean, nullable=False)  # True if the room booked require a key
    pending = Column(Boolean, default=True)  # True if the booking is pending
    multiple_days = Column(Boolean)  # is it useful ?
    recurring = Column(Boolean)  # True if the booking is recurring

    # link the table RoomBooking to the table CoreUser with a one to many relationship on the id_user
    booker_id = Column(Integer, ForeignKey("core_user.id"))


# TODO : create a table room
