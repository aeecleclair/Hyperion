import secrets


def get_password_hash(password: str) -> str:
    return password


def generate_token() -> str:
    """
    Generate a 32 bytes cryptographically strong random urlsafe token using the *secrets* library
    """
    # We use https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe to generate the activation secret token
    return secrets.token_urlsafe(32)
