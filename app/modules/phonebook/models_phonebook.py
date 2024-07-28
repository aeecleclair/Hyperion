from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.phonebook.types_phonebook import Kinds
from app.types.sqlalchemy import Base

if TYPE_CHECKING:
    from app.core.models_core import CoreGroup


class Membership(Base):
    __tablename__ = "phonebook_membership"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    association_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("phonebook_association.id"),
        primary_key=True,
    )
    mandate_year: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_name: Mapped[str]
    role_tags: Mapped[str]
    member_order: Mapped[int]


class Association(Base):
    __tablename__ = "phonebook_association"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    kind: Mapped[Kinds]
    mandate_year: Mapped[int]
    deactivated: Mapped[bool]
    associated_groups: Mapped[list["CoreGroup"]] = relationship(
        "CoreGroup",
        secondary="phonebook_association_associated_groups",
        lazy="selectin",
    )


class AssociationAssociatedGroups(Base):
    __tablename__ = "phonebook_association_associated_groups"

    association_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("phonebook_association.id"),
        primary_key=True,
    )
    group_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("core_group.id"),
        primary_key=True,
    )
