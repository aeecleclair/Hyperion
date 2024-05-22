from enum import Enum


class DocumentSignatureType(str, Enum):
    physical = "physical"
    material = "material"

    def __str__(self):
        return f"{self.name}<{self.value}>"


class PaymentType(str, Enum):
    cash = "cash"
    check = "check"
    helloasso = "HelloAsso"
    card = "card"
    archived = "archived"

    def __str__(self):
        return f"{self.name}<{self.value}>"


class AvailableMembership(str, Enum):
    aeecl = "AEECL"
    useecl = "USEECL"

    def __str__(self):
        return f"{self.name}<{self.value}>"


class CdrStatus(str, Enum):
    pending = "pending"
    online = "online"
    onsite = "onsite"
    closed = "closed"

    def __str__(self):
        return f"{self.name}<{self.value}>"


class CdrLogActionType(str, Enum):
    purchase_add = "purchase_add"
    purchase_delete = "purchase_delete"
    payment_add = "payment_add"
    payment_delete = "payment_delete"

    def __str__(self):
        return f"{self.name}<{self.value}>"
