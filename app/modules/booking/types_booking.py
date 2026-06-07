from enum import StrEnum


class Decision(StrEnum):
    approved = "approved"
    declined = "declined"
    pending = "pending"

    def __str__(self) -> str:
        return f"{self.name}<{self.value}>"
