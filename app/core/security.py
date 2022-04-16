import secrets

from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=13)
"""
In order to salt and hash password, we use a *passlib* [CryptContext](https://passlib.readthedocs.io/en/stable/narr/quickstart.html) object.

We use "bcrypt" to hash password, a different hash will be added automatically for each password. See [Auth0 Understanding bcrypt](https://auth0.com/blog/hashing-in-action-understanding-bcrypt/) for informations about bcrypt.
deprecated="auto" may be used to do password hash migration, see [Passlib hash migration](https://passlib.readthedocs.io/en/stable/narr/context-tutorial.html#deprecation-hash-migration).
It is improtant to use enough rounds while accounting for the hash computation time. Default is 12. 13 allows for a 0.5 seconds computing delay.
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
    Generate a 32 bytes cryptographically strong random urlsafe token using the *secrets* library
    """
    # We use https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe to generate the activation secret token
    return secrets.token_urlsafe(32)
