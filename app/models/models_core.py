"""Commun model files for all core in order to avoid circular import due to bidirectional relationship"""

from sqlalchemy import Column, ForeignKey, Integer, String, Date, DateTime
from sqlalchemy.orm import relationship

# from sqlalchemy.dialects.postgresql import UUID
# import uuid

from ..database import Base


class CoreMembership(
    Base
):  # Create a table for the many to many relationship between CoreUser and CoreGroup
    __tablename__ = "core_membership"

    id_user = Column(
        ForeignKey("core_user.id"), primary_key=True
    )  # The id of the user in the table CoreUser
    id_group = Column(
        ForeignKey("core_group.id"), primary_key=True
    )  # The id of the group in the table CoreGroup


class CoreUser(Base):
    __tablename__ = "core_user"

    id = Column(Integer, primary_key=True, index=True)  # Use UUID later
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    firstname = Column(String, nullable=False)
    nickname = Column(String)
    birthday = Column(Date)
    promo = Column(Integer)
    phone = Column(Integer)
    floor = Column(String, nullable=False)
    created_on = Column(DateTime)
    password = Column(String, nullable=False)  # the password is hashed

    groups = relationship(  # Create a many to many relationship between CoreUser and CoreGroup
        "CoreGroup",
        secondary="core_membership",
        back_populates="members",
        lazy="selectin",  # So that we don't have problems of implicite query that cause async issue
    )
    booker = relationship(
        "RoomBooking"
    )  # create a one to many relationship between CoreUser and RoomBooking


class CoreGroup(Base):
    __tablename__ = "core_group"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False, unique=True)
    description = Column(String)

    members = relationship(
        "CoreUser",
        secondary="core_membership",
        back_populates="groups",
        lazy="selectin",  # So that we don't have problems of implicite query that cause async issue
    )
