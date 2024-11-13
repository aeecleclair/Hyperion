from enum import Enum


class GroupType(str, Enum):
    """
    In Hyperion, each user may have multiple groups. Belonging to a group gives access to a set of specific endpoints.
    Usually, one or a few groups are associated to some rights over their corresponding module. For example a member of amap group is allowed to administrate the amap module

    A group may also allow using Hyperion OAuth/Openid connect capabilities to sign in to a specific external platform.

    Being member of admin only gives rights over admin specific endpoints. For example, an admin won't be able to administrate amap module
    """

    # Account types
    # student = "39691052-2ae5-4e12-99d0-7a9f5f2b0136"
    # formerstudent = "ab4c7503-41b3-11ee-8177-089798f1a4a5"
    # staff = "703056c4-be9d-475c-aa51-b7fc62a96aaa"
    # association = "29751438-103c-42f2-b09b-33fbb20758a7"
    # external = "b1cd979e-ecc1-4bd0-bc2b-4dad2ba8cded"
    # demo = "ae4d1866-e7d9-4d7f-bee7-e0dda24d8dd8"

    # Core groups
    admin = "0a25cb76-4b63-4fd3-b939-da6d9feabf28"
    AE = "45649735-866a-49df-b04b-a13c74fd5886"

    # Module related groups
    amap = "70db65ee-d533-4f6b-9ffa-a4d70a17b7ef"
    BDE = "53a669d6-84b1-4352-8d7c-421c1fbd9c6a"
    CAA = "6c6d7e88-fdb8-4e42-b2b5-3d3cfd12e7d6"
    cinema = "ce5f36e6-5377-489f-9696-de70e2477300"
    raid_admin = "e9e6e3d3-9f5f-4e9b-8e5f-9f5f4e9b8e5f"
    ph = "4ec5ae77-f955-4309-96a5-19cc3c8be71c"
    admin_cdr = "c1275229-46b2-4e53-a7c4-305513bb1a2a"
    eclair = "1f841bd9-00be-41a7-96e1-860a18a46105"

    # Auth related groups

    def __str__(self):
        return f"{self.name}<{self.value}>"


class AccountType(str, Enum):
    """
    Various account types that can be created in Hyperion.
    These values should match GroupType's. They are the lower level groups in Hyperion
    """

    student = "student"
    formerstudent = "formerstudent"
    staff = "staff"
    association = "association"
    external = "external"
    demo = "demo"

    def __str__(self):
        return f"{self.name}<{self.value}>"


def get_ecl_account_types() -> list[AccountType]:
    return [
        AccountType.student,
        AccountType.formerstudent,
        AccountType.staff,
        AccountType.association,
    ]


def get_account_types_except_external() -> list[AccountType]:
    return [
        AccountType.student,
        AccountType.formerstudent,
        AccountType.staff,
        AccountType.association,
        AccountType.demo,
    ]
