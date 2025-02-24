from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.types.sqlalchemy import Base

if TYPE_CHECKING:
    from app.core.users.models_users import CoreUser


class CoreMembership(Base):
    __tablename__ = "core_membership"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"), primary_key=True)
    # A description can be added to the membership
    # This can be used to note why a user is in a given group
    description: Mapped[str | None]


class CoreGroup(Base):
    __tablename__ = "core_group"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(index=True, unique=True)
    description: Mapped[str | None]

    members: Mapped[list["CoreUser"]] = relationship(
        "CoreUser",
        secondary="core_membership",
        back_populates="groups",
        default_factory=list,
    )
