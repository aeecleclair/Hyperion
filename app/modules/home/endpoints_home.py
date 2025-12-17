from app.core.groups.groups_type import AccountType
from app.modules.home.user_deleter_home import HomeUserDeleter
from app.types.module import Module

module = Module(
    root="home",
    tag="Home",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
    user_deleter=HomeUserDeleter(),
)
