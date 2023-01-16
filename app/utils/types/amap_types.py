from enum import Enum


class AmapSlotType(str, Enum):

    midi = "midi"
    soir = "soir"

    def __str__(self):
        return f"{self.name}<{self.value}"


class DeliveryStatusType(str, Enum):

    creation = "creation"  # Can edit date, add and remove products, no order possible
    orderable = "orderable"  # Ordering is possible, no edition possible
    locked = "locked"  # Can't order
    delivered = "delivered"  # Delivery can be archived
    archived = "archived"  # no longer returned

    def __str__(self):
        return f"{self.name}<{self.value}"
