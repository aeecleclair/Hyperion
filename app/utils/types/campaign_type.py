from enum import Enum


class ListType(str, Enum):
    """
    A list can be "Serios" or "Pipo". There will also be one "Blank" list by section that will be automatically added when the vote is open.
    """

    serio = "Serio"
    pipo = "Pipo"
    blank = "Blank"


class StatusType(str, Enum):
    """
    Status of the voting
    """

    waiting = "waiting"  # Lists and sections can be added and modified
    open = "open"  # No modification possible, votes possible
    closed = "closed"  # Nothing possible except for the counting
    counting = "counting"  # Admin can consult the results before making them public
    published = "published"  # All results are public
