from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class CoreMembership(Base):
    __tablename__ = "core_membership"

    user_id = Column(ForeignKey("core_user.id"), primary_key=True)
    group_id = Column(ForeignKey("core_group.id"), primary_key=True)


class CoreUser(Base):
    __tablename__ = "core_user"

    id = Column(Integer, primary_key=True, index=True)  # Use UID later
    login = Column(String)
    password = Column(String)  # the password is hashed
    name = Column(String)
    firstname = Column(String)
    nick = Column(String)
    birth = Column(String)
    promo = Column(String)
    floor = Column(String, default=None)
    email = Column(String, index=True)  # set unique=True later
    created_on = Column(String)

    groups = relationship(
        "CoreGroup", secondary="core_membership", back_populates="members"
    )


class CoreGroup(Base):
    __tablename__ = "core_group"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String)
    description = Column(String)

    members = relationship(
        "CoreUser", secondary="core_membership", back_populates="groups"
    )
