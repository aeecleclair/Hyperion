from sqlalchemy import Column, ForeignKey, Integer, String
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

    user_id: str = Column(String, ForeignKey("core_user.id"), nullable=False)
    association_id: str = Column(
        String, ForeignKey("phonebook_association.id"), nullable=False
    )
    role_id: str = Column(String, ForeignKey("phonebook_role.id"))

    mandate_year: int = Column(Integer, nullable=False)

    user: CoreUser = relationship("CoreUser")

    member_id: str = Column(String, primary_key=True, index=True)
