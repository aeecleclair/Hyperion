from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.phonebook.types_phonebook import Kinds
from app.types.sqlalchemy import Base

if TYPE_CHECKING:
    from app.core.core_endpoints.models_core import CoreGroup


class Membership(Base):
    __tablename__ = "phonebook_membership"

    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    association_id: Mapped[str] = mapped_column(
        ForeignKey("phonebook_association.id"),
        primary_key=True,
    )
    mandate_year: Mapped[int] = mapped_column(primary_key=True)
    role_name: Mapped[str]
    role_tags: Mapped[str]
    member_order: Mapped[int]


class Association(Base):
    __tablename__ = "phonebook_association"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(index=True)
    description: Mapped[str | None]
    kind: Mapped[Kinds]
    mandate_year: Mapped[int]
    deactivated: Mapped[bool]
    associated_groups: Mapped[list["CoreGroup"]] = relationship(
        "CoreGroup",
        secondary="phonebook_association_associated_groups",
        lazy="selectin",
        default_factory=list,
    )


class AssociationAssociatedGroups(Base):
    __tablename__ = "phonebook_association_associated_groups"

    association_id: Mapped[str] = mapped_column(
        ForeignKey("phonebook_association.id"),
        primary_key=True,
    )
    group_id: Mapped[str] = mapped_column(
        ForeignKey("core_group.id"),
        primary_key=True,
    )
