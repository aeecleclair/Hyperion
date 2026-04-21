from enum import StrEnum


class DocumentSignatureType(StrEnum):
    material = "material"
    numeric = "numeric"


class PaymentType(StrEnum):
    cash = "cash"
    check = "check"
    helloasso = "HelloAsso"
    card = "card"
    archived = "archived"


class CdrStatus(StrEnum):
    pending = "pending"
    online = "online"
    onsite = "onsite"
    closed = "closed"


class CdrLogActionType(StrEnum):
    purchase_add = "purchase_add"
    purchase_delete = "purchase_delete"
    payment_add = "payment_add"
    payment_delete = "payment_delete"
