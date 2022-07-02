"""Schemas file for endpoint /auth"""

from datetime import datetime

from pydantic import BaseModel


class TokenReq(BaseModel):
    code: str | None = None
    grant_type: str | None = None
    redirect_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    code_verifier: str | None = None


class AccessToken(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: str  # Subject: the user id
    iss: str | None = None
    aud: str | None = None
    iat: datetime | None = None
    nonce: str | None = None
    scopes: str = ""
    # exp and iat elements are added by the token generation function
