"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.models_core import CoreGroup, CoreUser


class Membership(Base):
    __tablename__ = "phonebook_membership"

    user_id: str = Column(ForeignKey("phonebook_members.id"), primary_key=True)
    association_id: str = Column(
        ForeignKey("phonebook_association.id"), primary_key=True
    )
    role_id: str = Column(ForeignKey("phonebook_role.id"), primary_key=True)


class Members(CoreUser):
    __tablename__ = "phonebook_members"

    # We use list["CoreGroup"] with quotes as CoreGroup is only defined after this class
    # Defining CoreUser after CoreGroup would cause a similar issue
    membership: list[Membership] = relationship(
        "CoreGroup",
        secondary="core_membership",
        back_populates="members",
    )


class Association(CoreGroup):
    __tablename__ = "phonebook_association"

    type: str = Column(String, nullable=False)
    membership: list[Membership] = relationship("Membership")


class Role(Base):
    __tablename__ = "phonebook_role"

    id: str = Column(String, primary_key=True, index=True, nullable=False)
    name: str = Column(String, nullable=False, index=True)
