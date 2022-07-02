from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.database import Base


class AuthorizationCode(Base):
    __tablename__ = "authorization_code"

    code: str = Column(String, primary_key=True, index=True)
    expire_on: datetime = Column(DateTime, nullable=False)
    scope: str | None = Column(String)
    redirect_uri: str | None = Column(String)
    user_id: str = Column(String, nullable=False)
    nonce: str | None = Column(String)
    code_challenge: str | None = Column(String)
    code_challenge_method: str | None = Column(String)
