"""
A collection of Pydantic validators
See https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
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


def email_normalizer(email: str) -> str:
    """
    Normalize the email address by lowercasing it.
    This function is intended to be used as a Pydantic validator:
    https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    """
    return email.lower()
