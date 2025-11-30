from app.core.groups.groups_type import AccountType
from app.modules.centralassociation.user_deleter_centralassociation import (
    CentralassociationUserDeleter,
)
from app.types.module import Module

module = Module(
    root="centralassociation",
    tag="Centralassociation",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
    user_deleter=CentralassociationUserDeleter(),
)
