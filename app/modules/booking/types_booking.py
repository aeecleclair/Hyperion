from enum import Enum


class Decision(str, Enum):
    approved = "approved"
    declined = "declined"
    pending = "pending"

    def __str__(self) -> str:
        return f"{self.name}<{self.value}>"
