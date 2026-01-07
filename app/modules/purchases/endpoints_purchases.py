from app.core.groups.groups_type import AccountType
from app.core.permissions.type_permissions import ModulePermissions
from app.types.module import Module


class PurchasesPermissions(ModulePermissions):
    access_purchases = "access_purchases"


module = Module(
    root="purchases",
    tag="Purchases",
    default_allowed_account_types=list(AccountType),
    factory=None,
    permissions=PurchasesPermissions,
)
