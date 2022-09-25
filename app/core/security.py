import secrets
from datetime import datetime, timedelta

from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_users
from app.models import models_core
from app.schemas import schemas_auth

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=13)
"""
In order to salt and hash password, we use a *passlib* [CryptContext](https://passlib.readthedocs.io/en/stable/narr/quickstart.html) object.

We use "bcrypt" to hash password, a different hash will be added automatically for each password. See [Auth0 Understanding bcrypt](https://auth0.com/blog/hashing-in-action-understanding-bcrypt/) for informations about bcrypt.
deprecated="auto" may be used to do password hash migration, see [Passlib hash migration](https://passlib.readthedocs.io/en/stable/narr/context-tutorial.html#deprecation-hash-migration).
It is improtant to use enough rounds while accounting for the hash computation time. Default is 12. 13 allows for a 0.5 seconds computing delay.
"""

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="auth/authorize",
    tokenUrl="auth/token",
    scheme_name="Authorization Code authentification",
)
"""
To generate JWT access tokens, we use a *FastAPI* OAuth2PasswordBearer object.
See [FastAPI documentation](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) about JWT.
"""

jwt_algorithme = "HS256"
"""
The algorithme used to generate JWT access tokens
"""


def get_password_hash(password: str) -> str:
    """
    Return a salted hash computed from password. The function use a bcrypt based *passlib* CryptContext.
    Both the salt and the algorithme identifier are included in the hash.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare `plain_password` against its salted hash representation `hashed_password`. The function use a bcrypt based *passlib* CryptContext.
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_token(nbytes=32) -> str:
    """
    Generate a `nbytes` bytes cryptographically strong random urlsafe token using the *secrets* library.

    By default the a 32 bytes token is generated.
    """
    # We use https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe to generate the activation secret token
    return secrets.token_urlsafe(32)


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> models_core.CoreUser | None:
    """
    Try to authenticate the user.
    If the user is unknown or the password is invalid return `None`. Else return the user's *CoreUser* representation.
    """
    user = await cruds_users.get_user_by_email(db=db, email=email)
    if not user:
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
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta is None:
        # We use the default value
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.dict(exclude_none=True)
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
