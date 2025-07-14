from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.groups.groups_type import AccountType
from app.core.schools.models_schools import CoreSchool
from app.types.floors_type import FloorsType
from app.types.sqlalchemy import Base

if TYPE_CHECKING:
    from app.core.groups.models_groups import CoreGroup


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
    school: Mapped[CoreSchool] = relationship(
        "CoreSchool",
        lazy="selectin",
        init=False,
    )

    @property
    def full_name(self) -> str:
        """
        Return the full name of the user, including first name, name and nickname if it exists.
        """
        if self.nickname:
            return f"{self.firstname} {self.name} ({self.nickname})"
        return f"{self.firstname} {self.name}"


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

    reset_token: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), unique=True)
    created_on: Mapped[datetime]
    expire_on: Mapped[datetime]


class CoreUserEmailMigrationRequest(Base):
    __tablename__ = "core_user_email_migration_request"

    confirmation_token: Mapped[str] = mapped_column(primary_key=True)
    # There can be only one request per user at a time
    # If a new request is made, old ones are removed
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), unique=True)
    new_email: Mapped[str]
    old_email: Mapped[str]
    created_on: Mapped[datetime]
    expire_on: Mapped[datetime]

    # If the user should become an external or a member user after the email change
    make_user_external: Mapped[bool] = mapped_column(default=False)
