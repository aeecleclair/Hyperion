"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from sqlalchemy import Column, ForeignKey, Integer, String

from app.database import Base

# from sqlalchemy.orm import relationship


class Membership(Base):
    __tablename__ = "phonebook_membership"

    id: str = Column(String, primary_key=True, index=True, nullable=False)
    user_id: str = Column(String, ForeignKey("core_user.id"), primary_key=True)
    association_id: str = Column(
        String, ForeignKey("phonebook_association.id"), primary_key=True
    )
    mandate_year: int = Column(Integer, nullable=False)
    role_name: str = Column(String, nullable=False)
    role_tags: str = Column(String, nullable=False)


class Association(Base):
    __tablename__ = "phonebook_association"

    id: str = Column(String, primary_key=True, index=True, nullable=False)
    name: str = Column(String, nullable=False, index=True)
    description: str = Column(String, nullable=True)
    kind: str = Column(String, nullable=False)
    mandate_year: int = Column(Integer, nullable=False)


class AttributedRoleTags(Base):
    __tablename__ = "phonebook_role_tags"

    tag: str = Column(String, primary_key=True)
    membership_id: str = Column(
        String, primary_key=True
    )
