from enum import Enum


class SchoolType(str, Enum):
    """
    In Hyperion, each user must have a school. Belonging to a school gives access to a set of specific endpoints.
    """

    # Account types
    no_school = "dce19aa2-8863-4c93-861e-fb7be8f610ed"
    centrale_lyon = "d9772da7-1142-4002-8b86-b694b431dfed"

    # Auth related groups

    def __str__(self):
        return f"{self.name}<{self.value}>"
