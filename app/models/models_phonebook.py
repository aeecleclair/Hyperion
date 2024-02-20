"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from sqlalchemy import Column, ForeignKey, String

from app.database import Base

# from sqlalchemy.orm import relationship


class Membership(Base):
    __tablename__ = "phonebook_membership"

    user_id: str = Column(String, ForeignKey("core_user.id"), primary_key=True)
    association_id: str = Column(
        String, ForeignKey("phonebook_association.id"), primary_key=True
    )

    role_id: str = Column(String, ForeignKey("phonebook_role.id"), primary_key=True)


class Association(Base):
    __tablename__ = "phonebook_association"

    id: str = Column(String, primary_key=True, index=True, nullable=False)
    name: str = Column(String, nullable=False, index=True)
    description: str = Column(String, nullable=True)
    type: str = Column(String, nullable=False)
    # membership: list[Membership] = relationship("Membership")


class Role(Base):
    __tablename__ = "phonebook_role"

    id: str = Column(String, primary_key=True, index=True, nullable=False)
    name: str = Column(String, nullable=False, index=True)
