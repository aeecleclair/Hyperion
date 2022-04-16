import secrets

from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from fastapi.security import OAuth2PasswordBearer
from app.cruds import cruds_users
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import models_core


from app.core.settings import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=13)
"""
In order to salt and hash password, we use a *passlib* [CryptContext](https://passlib.readthedocs.io/en/stable/narr/quickstart.html) object.

We use "bcrypt" to hash password, a different hash will be added automatically for each password. See [Auth0 Understanding bcrypt](https://auth0.com/blog/hashing-in-action-understanding-bcrypt/) for informations about bcrypt.
deprecated="auto" may be used to do password hash migration, see [Passlib hash migration](https://passlib.readthedocs.io/en/stable/narr/context-tutorial.html#deprecation-hash-migration).
It is improtant to use enough rounds while accounting for the hash computation time. Default is 12. 13 allows for a 0.5 seconds computing delay.
"""

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
"""
To generate JWT access tokens, we use a *FastAPI* OAuth2PasswordBearer object.
See [FastAPI documentation](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) about JWT.
"""

jwt_algorithme = "HS256"
"""
The algorithme used to generate JWT access tokens
"""


def password_validator(password: str) -> str:
    """
    Check the password strength, validity and remove trailing spaces.
    This function is intended to be used as a Pydantic validator:
    https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    """
    # TODO
    if len(password) < 6:
        raise ValueError("The password must be at least 6 characters long")
    return password.strip()


def get_password_hash(password: str) -> str:
    """
    Return a salted hash computed from password. The function use a bcrypt based *passlib* CryptContext.
    Both the salt and the algorithme identifier are included in the hash.
    """
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password) -> bool:
    """
    Compare `plain_password` against its salted hash representation `hashed_password`. The function use a bcrypt based *passlib* CryptContext.
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_token() -> str:
    """
    Generate a 32 bytes cryptographically strong random urlsafe token using the *secrets* library.
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
    data: dict,
    expires_delta: timedelta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
) -> str:
    """
    Create a JWT. The token is generated using ACCESS_TOKEN_SECRET_KEY secret.
    """
    to_encode = data.copy()
    expire_on = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire_on})
    encoded_jwt = jwt.encode(
        to_encode, settings.ACCESS_TOKEN_SECRET_KEY, algorithm=jwt_algorithme
    )
    return encoded_jwt
