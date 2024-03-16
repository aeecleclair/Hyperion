"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from datetime import date, datetime

from sqlalchemy import Date, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.types.floors_type import FloorsType
from app.types.sqlalchemy import Base, TZDateTime


class CoreMembership(Base):
    __tablename__ = "core_membership"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("core_group.id"), primary_key=True)
    # A description can be added to the membership
    # This can be used to note why a user is in a given group
    description: Mapped[str | None] = mapped_column(String)


class CoreUser(Base):
    __tablename__ = "core_user"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        index=True,
    )  # Use UUID later
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    firstname: Mapped[str] = mapped_column(String, nullable=False)
    nickname: Mapped[str | None] = mapped_column(String)
    birthday: Mapped[date | None] = mapped_column(Date)
    promo: Mapped[int | None] = mapped_column(Integer)
    phone: Mapped[str | None] = mapped_column(String)
    floor: Mapped[FloorsType | None] = mapped_column(Enum(FloorsType))
    created_on: Mapped[datetime | None] = mapped_column(TZDateTime)

    # Users that are externals (not members) won't be able to use all features
    # These, self registered, external users may exist for:
    # - accounts meant to be used by external services based on Hyperion SSO or Hyperion backend
    # - new users that need to do additional steps before being able to all features,
    #   like using a specific email address, going through an inscription process or being manually validated
    external: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # We use list["CoreGroup"] with quotes as CoreGroup is only defined after this class
    # Defining CoreUser after CoreGroup would cause a similar issue
    groups: Mapped[list["CoreGroup"]] = relationship(
        "CoreGroup",
        secondary="core_membership",
        back_populates="members",
    )


class CoreUserUnconfirmed(Base):
    __tablename__ = "core_user_unconfirmed"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # The email column should not be unique.
    # Someone can indeed create more than one user creation request,
    # for example after losing the previously received confirmation email.
    # For each user creation request, a row will be added in this table with a new token
    email: Mapped[str] = mapped_column(String, nullable=False)
    account_type: Mapped[str] = mapped_column(String, nullable=False)
    activation_token: Mapped[str] = mapped_column(String, nullable=False)
    created_on: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    expire_on: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    external: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CoreUserRecoverRequest(Base):
    __tablename__ = "core_user_recover_request"

    # The email column should not be unique.
    # Someone can indeed create more than one password reset request,
    email: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    reset_token: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)
    created_on: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    expire_on: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)


class CoreUserEmailMigrationCode(Base):
    """
    The ECL changed the email format for student users, requiring them to migrate their email.
    """

    __tablename__ = "core_user_email_migration_code"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    new_email: Mapped[str] = mapped_column(String, nullable=False)
    old_email: Mapped[str] = mapped_column(String, nullable=False)
    confirmation_token: Mapped[str] = mapped_column(
        String,
        nullable=False,
        primary_key=True,
    )


class CoreGroup(Base):
    __tablename__ = "core_group"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String)

    members: Mapped[list["CoreUser"]] = relationship(
        "CoreUser",
        secondary="core_membership",
        back_populates="groups",
    )


class ModuleAwareness(Base):
    """
    A ModuleAwareness is a table that stores the modules that are known by Hyperion.
    This allow to know which modules are new and should record their visibility in the database.
    """

    __tablename__ = "module_awareness"

    root: Mapped[str] = mapped_column(String, primary_key=True)
class CoreData(Base):
    """
    A table to store arbitrary data.

     - schema: the name of the schema allowing to deserialize the data.
     - data: the json data.

    Use `get_core_data` and `set_core_data` utils to interact with this table.
    """

    __tablename__ = "core_data"

    schema: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[str] = mapped_column(String, nullable=False)


class ModuleVisibility(Base):
    __tablename__ = "module_visibility"

    root: Mapped[str] = mapped_column(String, primary_key=True)
    allowed_group_id: Mapped[str] = mapped_column(String, primary_key=True)


class AlembicVersion(Base):
    """
    A table managed exclusively by Alembic, used to keep track of the database schema version.
    This model allows to have exactly the same tables in the models and in the database.
    Without this model, SQLAlchemy `conn.run_sync(Base.metadata.drop_all)` will ignore this table.

    WARNING: Hyperion should not modify this table.
    """

    __tablename__ = "alembic_version"

    version_num: Mapped[str] = mapped_column(String, primary_key=True)
