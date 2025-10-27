from app.core.groups.groups_type import AccountType
from app.core.permissions.type_permissions import ModulePermissions
from app.types.module import Module


class CentralisationPermissions(ModulePermissions):
    access_centralisation = "access_centralisation"


module = Module(
    root="centralisation",
    tag="Centralisation",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
    permissions=CentralisationPermissions,
)
