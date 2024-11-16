from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from app.types.sqlalchemy import Base


class AuthorizationCode(MappedAsDataclass, Base):
    __tablename__ = "authorization_code"

    code: Mapped[str] = mapped_column(primary_key=True, index=True)
    expire_on: Mapped[datetime]
    scope: Mapped[str | None]
    redirect_uri: Mapped[str | None]
    user_id: Mapped[str]
    nonce: Mapped[str | None]
    code_challenge: Mapped[str | None]
    code_challenge_method: Mapped[str | None]


class RefreshToken(MappedAsDataclass, Base):
    __tablename__ = "refresh_token"

    client_id: Mapped[str] = mapped_column(index=True, nullable=False)
    created_on: Mapped[datetime]
    expire_on: Mapped[datetime]
    token: Mapped[str] = mapped_column(
        index=True,
        primary_key=True,
        unique=True,
    )
    scope: Mapped[str | None]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))

    nonce: Mapped[str | None] = mapped_column(default=None)
    revoked_on: Mapped[datetime | None] = mapped_column(default=None)
