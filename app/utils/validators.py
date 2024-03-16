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
    nb_number, nb_special, nb_maj, nb_min = 0, 0, 0, 0
    for i in password:
        if i.isnumeric():
            nb_number += 1
        elif not i.isalpha():
            nb_special += 1
        elif i.isupper():
            nb_maj += 1
        elif i.islower():
            nb_min += 1

    if (
        len(password) < 6
        and nb_number < 1
        and nb_special < 1
        and nb_min < 1
        and nb_maj < 1
    ):
        raise ValueError(
            "The password must be at least 6 characters long and contain at least one number, one special character, one majuscule and one minuscule.",
        )
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
