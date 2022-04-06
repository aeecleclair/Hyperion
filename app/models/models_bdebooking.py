from sqlalchemy import Column, Integer, Boolean, DateTime, VARCHAR, TEXT, ForeignKey
from ..database import Base


class RoomBooking(Base):
    __tablename__ = "room_booking"

    id = Column(Integer, primary_key=True, index=True)  # Use UUID later
    booker = Column(VARCHAR)
    room = Column(VARCHAR)
    start = Column(DateTime)
    end = Column(DateTime)
    reason = Column(TEXT)
    notes = Column(TEXT)
    key = Column(Boolean)
    pending = Column(Boolean)
    multiple_days = Column(Boolean)
    recurring = Column(Boolean)

    # link the table RoomBooking to the table CoreUser with a one to many relationship on the id_user
    booker_id = Column(Integer, ForeignKey("core_user.id"))
