"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.groups.groups_type import AccountType
from app.types.floors_type import FloorsType
from app.types.membership import AvailableAssociationMembership
from app.types.sqlalchemy import Base, PrimaryKey


class CoreMembership(Base):
    __tablename__ = "core_membership"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"), primary_key=True)
    # A description can be added to the membership
    # This can be used to note why a user is in a given group
    description: Mapped[str | None]


class CoreUser(Base):
    __tablename__ = "core_user"

    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
    )  # Use UUID later
    email: Mapped[str] = mapped_column(unique=True, index=True)
    school_id: Mapped[UUID] = mapped_column(ForeignKey("core_school.id"))
    password_hash: Mapped[str]
    # Depending on the account type, the user may have different rights and access to different features
    # External users may exist for:
    # - accounts meant to be used by external services based on Hyperion SSO or Hyperion backend
    # - new users that need to do additional steps before being able to all features,
    #   like using a specific email address, going through an inscription process or being manually validated
    account_type: Mapped[AccountType]
    name: Mapped[str]
    firstname: Mapped[str]
    nickname: Mapped[str | None]
    birthday: Mapped[date | None]
    promo: Mapped[int | None]
    phone: Mapped[str | None]
    floor: Mapped[FloorsType | None]
    created_on: Mapped[datetime | None]

    # We use list["CoreGroup"] with quotes as CoreGroup is only defined after this class
    # Defining CoreUser after CoreGroup would cause a similar issue
    groups: Mapped[list["CoreGroup"]] = relationship(
        "CoreGroup",
        secondary="core_membership",
        back_populates="members",
        lazy="selectin",
        default_factory=list,
    )
    school: Mapped["CoreSchool"] = relationship(
        "CoreSchool",
        lazy="selectin",
        init=False,
    )


class CoreUserUnconfirmed(Base):
    __tablename__ = "core_user_unconfirmed"

    id: Mapped[str] = mapped_column(primary_key=True)
    # The email column should not be unique.
    # Someone can indeed create more than one user creation request,
    # for example after losing the previously received confirmation email.
    # For each user creation request, a row will be added in this table with a new token
    email: Mapped[str]
    activation_token: Mapped[str]
    created_on: Mapped[datetime]
    expire_on: Mapped[datetime]


class CoreUserRecoverRequest(Base):
    __tablename__ = "core_user_recover_request"

    # The email column should not be unique.
    # Someone can indeed create more than one password reset request,
    email: Mapped[str]
    user_id: Mapped[str]
    reset_token: Mapped[str] = mapped_column(primary_key=True)
    created_on: Mapped[datetime]
    expire_on: Mapped[datetime]


class CoreUserEmailMigrationCode(Base):
    """
    The ECL changed the email format for student users, requiring them to migrate their email.
    """

    __tablename__ = "core_user_email_migration_code"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    new_email: Mapped[str]
    old_email: Mapped[str]

    confirmation_token: Mapped[str] = mapped_column(
        String,
        nullable=False,
        primary_key=True,
    )

    # If the user should become an external or a member user after the email change
    make_user_external: Mapped[bool] = mapped_column(default=False)


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


class CoreSchool(Base):
    __tablename__ = "core_school"

    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(String, unique=True)
    email_regex: Mapped[str] = mapped_column(String)


class CoreAssociationMembership(Base):
    __tablename__ = "core_association_membership"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    membership: Mapped[AvailableAssociationMembership] = mapped_column(
        index=True,
    )
    start_date: Mapped[date]
    end_date: Mapped[date]


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
