"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.types.floors_type import FloorsType


class CoreMembership(Base):
    __tablename__ = "core_membership"

    user_id: str = Column(ForeignKey("core_user.id"), primary_key=True)
    group_id: str = Column(ForeignKey("core_group.id"), primary_key=True)
    # A description can be added to the membership
    # This can be used to note why a user is in a given group
    description: str | None = Column(String)


class CoreUser(Base):
    __tablename__ = "core_user"

    id: str = Column(String, primary_key=True, index=True)  # Use UUID later
    email: str = Column(String, unique=True, index=True, nullable=False)
    password_hash: str = Column(String, nullable=False)
    name: str = Column(String, nullable=False)
    firstname: str = Column(String, nullable=False)
    nickname: str | None = Column(String)
    birthday: date | None = Column(Date)
    promo: int | None = Column(Integer)
    phone: str | None = Column(String)
    floor: FloorsType = Column(Enum(FloorsType), nullable=False)
    created_on: datetime | None = Column(DateTime)

    # We use list["CoreGroup"] with quotes as CoreGroup is only defined after this class
    # Defining CoreUser after CoreGroup would cause a similar issue
    groups: list["CoreGroup"] = relationship(
        "CoreGroup",
        secondary="core_membership",
        back_populates="members",
    )


class CoreUserUnconfirmed(Base):
    __tablename__ = "core_user_unconfirmed"

    id: str = Column(String, primary_key=True)
    # The email column should not be unique.
    # Someone can indeed create more than one user creation request,
    # for example after losing the previously received confirmation email.
    # For each user creation request, a row will be added in this table with a new token
    email: str = Column(String, nullable=False)
    account_type: str = Column(String, nullable=False)
    activation_token: str = Column(String, nullable=False)
    created_on: datetime = Column(DateTime, nullable=False)
    expire_on: datetime = Column(DateTime, nullable=False)


class CoreUserRecoverRequest(Base):
    __tablename__ = "core_user_recover_request"

    # The email column should not be unique.
    # Someone can indeed create more than one password reset request,
    email: str = Column(String, nullable=False)
    user_id: str = Column(String, nullable=False)
    reset_token: str = Column(String, nullable=False, primary_key=True)
    created_on: datetime = Column(DateTime, nullable=False)
    expire_on: datetime = Column(DateTime, nullable=False)


class CoreGroup(Base):
    __tablename__ = "core_group"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, index=True, nullable=False, unique=True)
    description: str | None = Column(String)

    members: list["CoreUser"] = relationship(
        "CoreUser",
        secondary="core_membership",
        back_populates="groups",
    )
