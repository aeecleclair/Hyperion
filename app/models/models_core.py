"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from sqlalchemy import Column, ForeignKey, Integer, String, Date, DateTime, Enum
from sqlalchemy.orm import relationship
from app.utils.types.account_type import AccountType


from app.database import Base


class CoreMembership(Base):
    __tablename__ = "core_membership"

    id_user = Column(ForeignKey("core_user.id"), primary_key=True)
    id_group = Column(ForeignKey("core_group.id"), primary_key=True)


class CoreUser(Base):
    __tablename__ = "core_user"

    id = Column(String, primary_key=True, index=True)  # Use UUID later
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    firstname = Column(String, nullable=False)
    nickname = Column(String)
    birthday = Column(Date)
    promo = Column(Integer)
    phone = Column(Integer)
    floor = Column(String, nullable=False)
    created_on = Column(DateTime)
    account_type = Column(Enum(AccountType), nullable=False)

    groups = relationship(
        "CoreGroup",
        secondary="core_membership",
        back_populates="members",
    )


class CoreUserUnconfirmed(Base):
    __tablename__ = "core_user_unconfirmed"

    id = Column(String, primary_key=True)  # UUID
    email = Column(String, index=True, nullable=False)  # The email is not unique
    password_hash = Column(String)
    account_type = Column(String, nullable=False)
    activation_token = Column(String, nullable=False)
    created_on = Column(DateTime, nullable=False)
    expire_on = Column(DateTime, nullable=False)


class CoreGroup(Base):
    __tablename__ = "core_group"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False, unique=True)
    description = Column(String)

    members = relationship(
        "CoreUser",
        secondary="core_membership",
        back_populates="groups",
    )
