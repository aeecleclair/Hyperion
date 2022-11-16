from enum import Enum


class ListType(str, Enum):
    """
    A list can be "Serios" or "Pipo"
    """

    serio = "Serio"
    pipo = "Pipo"


class Status(str, Enum):
    """
    Status of the voting
    """

    waiting = "waiting"  # Lists and sections can be added and modified
    opened = "opened"  # No modification possible, votes possible
    closed = "closed"  # Nothing possible except for the counting
    counted = "counted"  # Consult the results or delete every votes
