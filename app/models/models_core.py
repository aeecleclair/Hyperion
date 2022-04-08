"""Commun model files for all core in order to avoid circular import due to bidirectional relationship"""

from sqlalchemy import Column, ForeignKey, Integer, String, Date, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class CoreMembership(Base):
    __tablename__ = "core_membership"

    id_user = Column(ForeignKey("core_user.id"), primary_key=True)
    id_group = Column(ForeignKey("core_group.id"), primary_key=True)


class CoreUser(Base):
    __tablename__ = "core_user"

    id = Column(Integer, primary_key=True, index=True)  # Use UID later
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

    groups = relationship(
        "CoreGroup",
        secondary="core_membership",
        back_populates="members",
    )


class CoreGroup(Base):
    __tablename__ = "core_group"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False, unique=True)
    description = Column(String)

    members = relationship(
        "CoreUser",
        secondary="core_membership",
        back_populates="groups",
    )
