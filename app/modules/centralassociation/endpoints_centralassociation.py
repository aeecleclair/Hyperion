from app.core.groups.groups_type import AccountType
from app.core.permissions.type_permissions import ModulePermissions
from app.types.module import Module


class CentralassociationPermissions(ModulePermissions):
    access_centralassociation = "access_centralassociation"


module = Module(
    root="centralassociation",
    tag="Centralassociation",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
    permissions=CentralassociationPermissions,
)
