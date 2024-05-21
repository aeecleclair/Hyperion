from enum import Enum


class DocumentSignatureType(str, Enum):
    physical = "physical"
    material = "material"

    def __str__(self):
        return f"{self.name}<{self.value}"


class PaymentType(str, Enum):
    cash = "cash"
    check = "check"
    helloasso = "HelloAsso"
    card = "card"
    archived = "archived"

    def __str__(self):
        return f"{self.name}<{self.value}"


class AvailableMembership(str, Enum):
    aeecl = "AEECL"
    useecl = "USEECL"

    def __str__(self):
        return f"{self.name}<{self.value}"
