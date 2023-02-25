from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.models_core import CoreUser


class Role(Base):
    __tablename__ = "phonebook_role"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, nullable=False, unique=True)


class Association(Base):
    __tablename__ = "phonebook_association"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, nullable=False, unique=True)


class Member(Base):
    __tablename__ = "phonebook_member"

    user_id: str = Column(
        String, ForeignKey("core_user.id"), primary_key=True, index=True
    )
    association_id: str = Column(
        String, ForeignKey("phonebook_association.id"), primary_key=True
    )
    role_id: str = Column(String, ForeignKey("phonebook_role.id"))

    user: CoreUser = relationship("CoreUser")
