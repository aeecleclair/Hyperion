"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# from sqlalchemy.orm import relationship


class Membership(Base):
    __tablename__ = "phonebook_membership"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("core_user.id"), primary_key=True)
    association_id: Mapped[str] = mapped_column(
        String, ForeignKey("phonebook_association.id"), primary_key=True
    )
    mandate_year: Mapped[int] = mapped_column(Integer, nullable=False)
    role_name: Mapped[str] = mapped_column(String, nullable=False)
    role_tags: Mapped[str] = mapped_column(String, nullable=False)


class Association(Base):
    __tablename__ = "phonebook_association"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    mandate_year: Mapped[int] = mapped_column(Integer, nullable=False)


class AttributedRoleTags(Base):
    __tablename__ = "phonebook_role_tags"

    tag: Mapped[str] = mapped_column(String, primary_key=True)
    membership_id: Mapped[str] = mapped_column(
        String, primary_key=True
    )
