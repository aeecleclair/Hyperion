from enum import Enum


class GroupType(str, Enum):
    """
    In Hyperion, each user may have multiple groups. Belonging to a group gives access to a set of specific endpoint.
    Usually, one or a few groups are associated to some rights over their corresponding module. For exemple a member of amap group is allowed to administrate the amap module

    A group may also allows to use Hyperion OAuth/Openid connect capabilities to sign into a specific external platform.

    Being member of admin only gives rights over admin specific endpoints. For example, an admin won't be able to administrate amap module
    """

    # Account types
    student = "39691052-2ae5-4e12-99d0-7a9f5f2b0136"
    staff = "703056c4-be9d-475c-aa51-b7fc62a96aaa"
    association = "29751438-103c-42f2-b09b-33fbb20758a7"

    # Core groups
    admin = "0a25cb76-4b63-4fd3-b939-da6d9feabf28"
    amap = "70db65ee-d533-4f6b-9ffa-a4d70a17b7ef"
    BDE = "53a669d6-84b1-4352-8d7c-421c1fbd9c6a"

    # Module related groups

    # Auth related groupes

    def __str__(self):
        return f"{self.name}<{self.value}>"


class AccountType(str, Enum):
    """
    Various account type that can be created in Hyperion.
    These values should match GroupType's. They are the lower level groups in Hyperion
    """

    student = GroupType.student.value
    staff = GroupType.staff.value
    association = GroupType.association.value

    def __str__(self):
        return f"{self.name}<{self.value}>"
