from app.core.groups.groups_type import AccountType
from app.core.permissions.type_permissions import ModulePermissions
from app.types.module import Module


class HomePermissions(ModulePermissions):
    access_home = "access_home"


module = Module(
    root="home",
    tag="Home",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
    permissions=HomePermissions,
)
