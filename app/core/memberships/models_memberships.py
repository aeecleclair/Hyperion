from datetime import date
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.users.models_users import CoreUser
from app.types.sqlalchemy import Base, PrimaryKey


class CoreAssociationMembership(Base):
    __tablename__ = "core_association_membership"

    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(unique=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"))


class CoreAssociationUserMembership(Base):
    __tablename__ = "core_association_user_membership"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    association_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("core_association_membership.id"),
        index=True,
    )
    start_date: Mapped[date]
    end_date: Mapped[date]

    user: Mapped[CoreUser] = relationship(
        "CoreUser",
        lazy="joined",
        init=False,
    )
