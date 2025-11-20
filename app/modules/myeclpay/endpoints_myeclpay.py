from app.core.groups.groups_type import AccountType
from app.core.permissions.type_permissions import ModulePermissions
from app.types.module import Module


class MyECLPayPermissions(ModulePermissions):
    access_payment = "access_payment"


module = Module(
    root="payment",
    tag="MyECLPay",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
    permissions=MyECLPayPermissions,
)
