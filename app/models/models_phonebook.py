"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from sqlalchemy import Column, ForeignKey, Integer, String

from app.database import Base

# from sqlalchemy.orm import relationship


class Membership(Base):
    __tablename__ = "phonebook_membership"

    user_id: str = Column(String, ForeignKey("core_user.id"), primary_key=True)
    association_id: str = Column(
        String, ForeignKey("phonebook_association.id"), primary_key=True
    )
    role_tags: str = Column(String, nullable=False)
    role_name: str = Column(String)
    mandate_year: int = Column(Integer, nullable=False)


class RoleTags(Base):
    __tablename__ = "phonebook_role_tags"
    tag_name: str = Column(String, primary_key=True)
