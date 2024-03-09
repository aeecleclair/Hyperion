"""Common model files for all core in order to avoid circular import due to bidirectional relationship"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.types.floors_type import FloorsType


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
        String, primary_key=True, index=True
    )  # Use UUID later
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    firstname: Mapped[str] = mapped_column(String, nullable=False)
    nickname: Mapped[str | None] = mapped_column(String)
    birthday: Mapped[date | None] = mapped_column(Date)
    promo: Mapped[int | None] = mapped_column(Integer)
    phone: Mapped[str | None] = mapped_column(String)
    floor: Mapped[FloorsType] = mapped_column(Enum(FloorsType), nullable=False)
    created_on: Mapped[datetime | None] = mapped_column(DateTime)

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
    created_on: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expire_on: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CoreUserRecoverRequest(Base):
    __tablename__ = "core_user_recover_request"

    # The email column should not be unique.
    # Someone can indeed create more than one password reset request,
    email: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    reset_token: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)
    created_on: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expire_on: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CoreUserEmailMigrationCode(Base):
    """
    The ECL changed the email format for student users, requiring them to migrate their email.
    """

    __tablename__ = "core_user_email_migration_code"

    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), primary_key=True)
    new_email: Mapped[str] = mapped_column(String, nullable=False)
    old_email: Mapped[str] = mapped_column(String, nullable=False)
    confirmation_token: Mapped[str] = mapped_column(
        String, nullable=False, primary_key=True
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
