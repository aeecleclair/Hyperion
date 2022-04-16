from enum import Enum


class AccountType(str, Enum):
    """
    Various account type that can be created in Hyperion
    """

    student = "39691052-2ae5-4e12-99d0-7a9f5f2b0136"
    staff = "703056c4-be9d-475c-aa51-b7fc62a96aaa"
    association = "29751438-103c-42f2-b09b-33fbb20758a7"

    def __str__(self):
        return f"{self.name}<{self.value}>"


class GroupType(str, Enum):

    student = "39691052-2ae5-4e12-99d0-7a9f5f2b0136"
    staff = "703056c4-be9d-475c-aa51-b7fc62a96aaa"
    association = "29751438-103c-42f2-b09b-33fbb20758a7"

    admin = "0a25cb76-4b63-4fd3-b939-da6d9feabf28"

    def __str__(self):
        return f"{self.name}<{self.value}>"
