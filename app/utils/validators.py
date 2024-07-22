import re

import zxcvbn

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
    password = password.strip()
    if not re.fullmatch(
        r"(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$€%^&*\(\)_+\-.,.?\":\{\}|<>'/;\[\]]).*",
        password,
    ):
        raise ValueError(
            "The password must contain at least one number, one special character, one majuscule and one minuscule.",
        )
    result = zxcvbn.zxcvbn(password)
    if not result["score"] == 4:
        raise ValueError(
            result["feedback"],
        )

    return password


def email_normalizer(email: str) -> str:
    """
    Normalize the email address by lowercasing it. We also remove trailing spaces.
    This function is intended to be used as a Pydantic validator:
    https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    """
    return email.lower().strip()


def trailing_spaces_remover(value: str | None) -> str | None:
    """
    Remove trailing spaces.

    If the value is None, it is returned as is. The validator can thus be used for optional values.

    This function is intended to be used as a Pydantic validator:
    https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    """
    if value is not None:
        return value.strip()
    return value
