from enum import Enum


class GroupType(str, Enum):
    """
    In Hyperion, each user may have multiple groups. Belonging to a group gives access to a set of specific endpoints.
    Usually, one or a few groups are associated to some rights over their corresponding module. For example a member of amap group is allowed to administrate the amap module

    A group may also allow using Hyperion OAuth/Openid connect capabilities to sign in to a specific external platform.

    Being member of admin only gives rights over admin specific endpoints. For example, an admin won't be able to administrate amap module
    """

    # Core groups
    admin = "0a25cb76-4b63-4fd3-b939-da6d9feabf28"

    # Auth related groups

    def __str__(self):
        return f"{self.name}<{self.value}>"


class AccountType(str, Enum):
    """
    Various account types that can be created in Hyperion.
    These values should match GroupType's. They are the lower level groups in Hyperion
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


def get_account_types_except_externals() -> list[AccountType]:
    return [
        AccountType.student,
        AccountType.former_student,
        AccountType.staff,
        AccountType.association,
        AccountType.demo,
        AccountType.other_school_student,
    ]
