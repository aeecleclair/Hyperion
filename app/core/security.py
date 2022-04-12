import secrets


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
    return password


def generate_token() -> str:
    """
    Generate a 32 bytes cryptographically strong random urlsafe token using the *secrets* library
    """
    # We use https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe to generate the activation secret token
    return secrets.token_urlsafe(32)
