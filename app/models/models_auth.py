from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuthorizationCode(Base):
    __tablename__ = "authorization_code"

    code: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    expire_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scope: Mapped[str | None] = mapped_column(String)
    redirect_uri: Mapped[str | None] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    nonce: Mapped[str | None] = mapped_column(String)
    code_challenge: Mapped[str | None] = mapped_column(String)
    code_challenge_method: Mapped[str | None] = mapped_column(String)


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    client_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expire_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token: Mapped[str] = mapped_column(
        String, index=True, primary_key=True, unique=True, nullable=False
    )
    scope: Mapped[str | None] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"), nullable=False)
    nonce: Mapped[str | None] = mapped_column(String)
