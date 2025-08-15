from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
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

    @property
    def group_ids(self) -> list[str]:
        return [group.id for group in self.groups]


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

    # Users will be automatically added to this group when they activate their account
    default_group_id: Mapped[str | None] = mapped_column(
        ForeignKey("core_group.id"),
    )


class CoreUserInvitation(Base):
    """
    Registration can be limited to specific invited users.
    """

    __tablename__ = "core_user_invitation"

    email: Mapped[str] = mapped_column(primary_key=True)

    default_group_id: Mapped[str | None] = mapped_column(
        ForeignKey("core_group.id"),
    )


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
