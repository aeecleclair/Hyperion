"""
A collection of Pydantic validators
See https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
"""

import phonenumbers


def password_validator(password: str) -> str:
    """
    Check the password strength, validity and remove trailing spaces.
    This function is intended to be used as a Pydantic validator:
    https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    """
    # TODO
    if len(password) < 6:
        raise ValueError("The password must be at least 6 characters long")  # noqa: TRY003 # this line is intended to be replaced
    return password.strip()


def phone_formatter(phone: str) -> str:
    """
    Verify that a phone number is parsable.
    This function is intended to be used as a Pydantic validator:
    https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    """

    # We need to raise a ValueError for Pydantic to catch it and return an error response
    try:
        parsed_phone = phonenumbers.parse(phone, None)
    except Exception as error:
        raise ValueError(f"Invalid phone number: {error}")  # noqa: B904, TRY003
    if not phonenumbers.is_possible_number(parsed_phone):
        raise ValueError("Invalid phone number, number is not possible")  # noqa: TRY003
    if not phonenumbers.is_valid_number(parsed_phone):
        raise ValueError("Invalid phone number, number is not valid")  # noqa: TRY003
    return phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)


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
