from sqlalchemy import (
    Column,
    ForeignKey,
    String,
)

from app.database import Base

class Room(Base):
    __tablename__ = "room"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, nullable=False, unique=True)
    group: str = Column(String, nullable=False)


class RoomAdmin(Base):
    __tablename__ = "room_admin"

    user_id: str = Column(ForeignKey("user.id"), primary_key=True)
    room_id: str = Column(ForeignKey("room.id"), primary_key=True)


class Member(Base):
    __tablename__ = "member"

    user_id: str = Column(ForeignKey("user.id"), primary_key=True)
    post: str = Column(String, nullable=False)
    group: str = Column(String, nullable=False)