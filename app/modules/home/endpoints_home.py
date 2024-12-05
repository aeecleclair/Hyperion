from app.core.groups.groups_type import AccountType
from app.types.module import Module

module = Module(
    root="home",
    tag="Home",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)
