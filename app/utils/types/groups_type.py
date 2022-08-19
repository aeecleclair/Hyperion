from enum import Enum


class GroupType(str, Enum):

    student = "39691052-2ae5-4e12-99d0-7a9f5f2b0136"
    staff = "703056c4-be9d-475c-aa51-b7fc62a96aaa"
    association = "29751438-103c-42f2-b09b-33fbb20758a7"

    admin = "0a25cb76-4b63-4fd3-b939-da6d9feabf28"
    BDE = "53a669d6-84b1-4352-8d7c-421c1fbd9c6a"

    def __str__(self):
        return f"{self.name}<{self.value}>"


class AccountType(str, Enum):
    """
    Various account type that can be created in Hyperion.
    These values should match GroupType's
    """

    student = GroupType.student.value
    staff = GroupType.staff.value
    association = GroupType.association.value

    def __str__(self):
        return f"{self.name}<{self.value}>"
