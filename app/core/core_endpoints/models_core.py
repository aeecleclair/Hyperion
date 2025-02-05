"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.groups.groups_type import AccountType
from app.types.floors_type import FloorsType
from app.types.membership import AvailableAssociationMembership
from app.types.sqlalchemy import Base, PrimaryKey


class CoreAssociationMembership(Base):
    __tablename__ = "core_association_membership"

    id: Mapped[PrimaryKey]
    name: Mapped[str]

    users_memberships: Mapped[list["CoreAssociationUserMembership"]] = relationship(
        "CoreAssociationUserMembership",
        primaryjoin="CoreAssociationUserMembership.association_membership_id == CoreAssociationMembership.id",
        lazy="selectin",
        default_factory=list,
    )


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

    user: Mapped["CoreUser"] = relationship(
        "CoreUser",
        lazy="joined",
        init=False,
    )


class CoreData(Base):
    """
    A table to store arbitrary data.

     - schema: the name of the schema allowing to deserialize the data.
     - data: the json data.

    Use `get_core_data` and `set_core_data` utils to interact with this table.
    """

    __tablename__ = "core_data"

    schema: Mapped[str] = mapped_column(primary_key=True)
    data: Mapped[str]


class ModuleGroupVisibility(Base):
    __tablename__ = "module_group_visibility"

    root: Mapped[str] = mapped_column(primary_key=True)
    allowed_group_id: Mapped[str] = mapped_column(primary_key=True)


class ModuleAccountTypeVisibility(Base):
    __tablename__ = "module_account_type_visibility"

    root: Mapped[str] = mapped_column(primary_key=True)
    allowed_account_type: Mapped[AccountType] = mapped_column(primary_key=True)


class AlembicVersion(Base):
    """
    A table managed exclusively by Alembic, used to keep track of the database schema version.
    This model allows to have exactly the same tables in the models and in the database.
    Without this model, SQLAlchemy `conn.run_sync(Base.metadata.drop_all)` will ignore this table.

    WARNING: Hyperion should not modify this table.
    """

    __tablename__ = "alembic_version"

    version_num: Mapped[str] = mapped_column(primary_key=True)
