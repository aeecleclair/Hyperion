from app.core.groups.groups_type import AccountType
from app.types.module import Module

module = Module(
    root="payment",
    tag="MyPayment",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
)
