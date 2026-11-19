import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.groups.models_groups import CoreGroup
from app.core.users.models_users import CoreUser
from app.types.sqlalchemy import Base, PrimaryKey


class VerificationContext(Base):
    __tablename__ = "identity_verification_context"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    archived: Mapped[bool]
    group_id: Mapped[str] = mapped_column(
        ForeignKey("core_group.id"),
    )

    group: Mapped[CoreGroup] = relationship(
        init=False,
    )


class VerificationScan(Base):
    __tablename__ = "identity_verification_scan"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    verification_context_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identity_verification_context.id"),
    )
    datetime: Mapped[datetime]
    scanner_user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )

    user: Mapped[CoreUser] = relationship(
        init=False,
        foreign_keys=[user_id],
    )


class IdentityToken(Base):
    __tablename__ = "identity_token"

    id: Mapped[PrimaryKey]
    token: Mapped[str] = mapped_column(unique=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    expire_on: Mapped[datetime]

    user: Mapped[CoreUser] = relationship(init=False)
