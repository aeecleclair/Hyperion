from enum import Enum


class ListType(str, Enum):
    """
    A list can be "Serios" or "Pipo"
    """

    serio = "Serio"
    pipo = "Pipo"
