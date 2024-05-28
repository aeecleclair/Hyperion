from enum import Enum


class DocumentSignatureType(str, Enum):
    material = "material"
    numeric = "numeric"


class PaymentType(str, Enum):
    cash = "cash"
    check = "check"
    helloasso = "HelloAsso"
    card = "card"
    archived = "archived"


class AvailableMembership(str, Enum):
    aeecl = "AEECL"
    useecl = "USEECL"


class CdrStatus(str, Enum):
    pending = "pending"
    online = "online"
    onsite = "onsite"
    closed = "closed"


class CdrLogActionType(str, Enum):
    purchase_add = "purchase_add"
    purchase_delete = "purchase_delete"
    payment_add = "payment_add"
    payment_delete = "payment_delete"
