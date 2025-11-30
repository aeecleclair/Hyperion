from app.core.groups.groups_type import AccountType
from app.modules.centralisation.user_deleter_centralisation import user_deleter
from app.types.module import Module

module = Module(
    root="centralisation",
    tag="Centralisation",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
    user_deleter=user_deleter,
)
