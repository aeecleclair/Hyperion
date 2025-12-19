from enum import Enum


class GroupType(str, Enum):
    """
    In Hyperion, each user may have multiple groups. Belonging to a group gives access to a set of specific permissions.

    The only hardcoded group is the admin group.
    Being member of admin gives rights over all endpoints except identity based enpoints (i.e an admin won't be able to act in place of an association or a person)

    Other groups are created by the admin and can be associated with a set of permissions.
    """

    admin = "0a25cb76-4b63-4fd3-b939-da6d9feabf28"


class AccountType(str, Enum):
    """
    Various account types that can be created in Hyperion.
    Each account type is associated with a set of permissions.
    """

    student = "student"
    former_student = "former_student"
    staff = "staff"
    association = "association"
    external = "external"
    other_school_student = "other_school_student"
    demo = "demo"

    def __str__(self):
        return f"{self.name}<{self.value}>"


def get_ecl_account_types() -> list[AccountType]:
    return [
        AccountType.student,
        AccountType.former_student,
        AccountType.staff,
        AccountType.association,
    ]


def get_schools_account_types() -> list[AccountType]:
    return [
        AccountType.student,
        AccountType.former_student,
        AccountType.staff,
        AccountType.association,
        AccountType.other_school_student,
    ]


def get_account_types_except_externals() -> list[AccountType]:
    return [
        AccountType.student,
        AccountType.former_student,
        AccountType.staff,
        AccountType.association,
        AccountType.demo,
        AccountType.other_school_student,
    ]
