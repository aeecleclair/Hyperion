from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String

from app.database import Base


class AuthorizationCode(Base):
    __tablename__ = "authorization_code"

    code: str = Column(String, primary_key=True, index=True)
    expire_on: datetime = Column(DateTime(timezone=True), nullable=False)
    scope: str | None = Column(String)
    redirect_uri: str | None = Column(String)
    user_id: str = Column(String, nullable=False)
    nonce: str | None = Column(String)
    code_challenge: str | None = Column(String)
    code_challenge_method: str | None = Column(String)


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    client_id: str = Column(String, index=True, nullable=False)
    created_on: datetime = Column(DateTime, nullable=False)
    expire_on: datetime = Column(DateTime, nullable=False)
    revoked_on: datetime | None = Column(DateTime)
    token: str = Column(
        String, index=True, primary_key=True, unique=True, nullable=False
    )
    scope: str | None = Column(String)
    user_id: str = Column(ForeignKey("core_user.id"), nullable=False)
    nonce: str | None = Column(String)
