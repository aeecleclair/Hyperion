from enum import Enum


class RaffleStatusType(str, Enum):
    creation = "creation"  # Can edit every parameter
    open = "open"  # Ordering is possible, no edition possible
    lock = "lock"  # Can't order

    def __str__(self):
        return f"{self.name}<{self.value}"
