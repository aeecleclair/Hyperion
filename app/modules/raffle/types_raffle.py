from enum import StrEnum


class RaffleStatusType(StrEnum):
    creation = "creation"  # Can edit every parameter
    open = "open"  # Ordering is possible, no edition possible
    lock = "lock"  # Can't order
