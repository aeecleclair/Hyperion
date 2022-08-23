from enum import Enum


class Decision(str, Enum):
    approved = "approved"
    declined = "declined"
    pending = "pending"

    def __str__(self):
        return f"{self.name}<{self.value}>"
