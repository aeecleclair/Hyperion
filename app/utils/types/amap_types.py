from enum import Enum


class AmapSlotType(str, Enum):

    midi = "midi"
    soir = "soir"

    def __str__(self):
        return f"{self.name}<{self.value}"
