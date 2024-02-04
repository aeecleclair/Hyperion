import secrets
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_users
from app.models import models_core
from app.schemas import schemas_auth

"""
In order to salt and hash password, we the bcrypt hashing function (see https://en.wikipedia.org/wiki/Bcrypt).

A different salt will be added automatically for each password. See [Auth0 Understanding bcrypt](https://auth0.com/blog/hashing-in-action-understanding-bcrypt/) for information about bcrypt.
It is important to use enough rounds while accounting for the hash computation time. Default is 12. 13 allows for a 0.5 seconds computing delay.
"""

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="auth/authorize",
    tokenUrl="auth/token",
    scheme_name="Authorization Code authentication",
)
"""
To generate JWT access tokens, we use a *FastAPI* OAuth2PasswordBearer object.
See [FastAPI documentation](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) about JWT.
"""

jwt_algorithme = "HS256"
"""
The algorithme used to generate JWT access tokens
"""


def generate_token(nbytes=32) -> str:
    """
    Generate a `nbytes` bytes cryptographically strong random urlsafe token using the *secrets* library.

    By default, a 32 bytes token is generated.
    """
    # We use https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe to generate the activation secret token
    return secrets.token_urlsafe(nbytes)


def get_password_hash(password: str) -> str:
    """
    Return a salted hash computed from password.
    Both the salt and the algorithm identifier are included in the hash.
    """
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=13))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """
    Compare `plain_password` against its salted hash representation `hashed_password`.

    We genrerate a fake_hash for the case where hashed_password=None (ie the email isn't valid) to simulate the delay a real verification would have taken.
    This is useful to limit timing attacks that could be used to guess valid emails.
    """
    fake_hash = bcrypt.hashpw(generate_token(12).encode("utf-8"), bcrypt.gensalt(13))
    if hashed_password is None:
        return bcrypt.checkpw(plain_password.encode("utf-8"), fake_hash)
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> models_core.CoreUser | None:
    """
    Try to authenticate the user.
    If the user is unknown or the password is invalid return `None`. Else return the user's *CoreUser* representation.
    """
    user = await cruds_users.get_user_by_email(db=db, email=email)
    if not user:
        # In order to prevent timing attacks, we simulate the delay the password validation would have taken if the account existed
        verify_password("", None)

        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(
    settings: Settings,
    data: schemas_auth.TokenData,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT. The token is generated using ACCESS_TOKEN_SECRET_KEY secret.
    """
    if expires_delta is None:
        # We use the default value
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.dict(exclude_none=True)
    iat = datetime.utcnow()
    expire_on = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire_on, "iat": iat})
    encoded_jwt = jwt.encode(
        to_encode, settings.ACCESS_TOKEN_SECRET_KEY, algorithm=jwt_algorithme
    )
    return encoded_jwt


def create_access_token_RS256(
    settings: Settings,
    data: schemas_auth.TokenData,
    additional_data: dict[str, Any] = {},
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT. The token is generated using the RSA_PRIVATE_KEY secret.

    The token will contain the data from `data` and `additional_data`.
    """
    if expires_delta is None:
        # We use the default value
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = additional_data
    to_encode.update(data.dict(exclude_none=True))

    iat = datetime.utcnow()
    expire_on = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire_on, "iat": iat})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.RSA_PRIVATE_KEY,
        algorithm="RS256",
        headers={
            "kid": "RSA-JWK-1"
        },  # The kid allows to identify the key to use to decode the JWT, and should be the same as the kid in the JWK Set.
    )
    return encoded_jwt
