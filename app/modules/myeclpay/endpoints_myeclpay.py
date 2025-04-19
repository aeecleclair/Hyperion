from app.core.groups.groups_type import AccountType
from app.types.module import Module

module = Module(
    root="payment",
    tag="MyECLPay",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)
