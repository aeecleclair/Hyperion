from app.core.groups.groups_type import AccountType
from app.modules.purchases.user_deleter_purchases import user_deleter
from app.types.module import Module

module = Module(
    root="purchases",
    tag="Purchases",
    default_allowed_account_types=[AccountType.student, AccountType.external],
    factory=None,
    user_deleter=user_deleter,
)
