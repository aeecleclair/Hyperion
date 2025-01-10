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
    AE = "45649735-866a-49df-b04b-a13c74fd5886"
    # payment = "5571adfd-47fc-4dde-a44b-6e1289476499"

    # Module related groups
    amap = "70db65ee-d533-4f6b-9ffa-a4d70a17b7ef"
    BDE = "53a669d6-84b1-4352-8d7c-421c1fbd9c6a"
    CAA = "6c6d7e88-fdb8-4e42-b2b5-3d3cfd12e7d6"
    cinema = "ce5f36e6-5377-489f-9696-de70e2477300"
    raid_admin = "e9e6e3d3-9f5f-4e9b-8e5f-9f5f4e9b8e5f"
    ph = "4ec5ae77-f955-4309-96a5-19cc3c8be71c"
    admin_cdr = "c1275229-46b2-4e53-a7c4-305513bb1a2a"
    eclair = "1f841bd9-00be-41a7-96e1-860a18a46105"
    BDS = "61af3e52-7ef9-4608-823a-39d51e83d1db"

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
