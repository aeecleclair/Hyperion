"""
A collection of Pydantic validators
See https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
"""


from datetime import datetime, timedelta, timezone


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


def paris_time_zone_converter(date_time: datetime) -> datetime:
    """
    Convert a aware/naive datetime to an aware datetime based on Paris (UTC +2) timezone

    This function is intended to be used as a Pydantic validator:
    https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    """

    return date_time.astimezone(timezone(timedelta(hours=2)))
