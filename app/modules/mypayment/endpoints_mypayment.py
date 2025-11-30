from app.core.groups.groups_type import AccountType
from app.dependencies import get_settings
from app.types.module import Module

DISPLAY_NAME = get_settings().school.payment_name

module = Module(
    root="mypayment",
    tag=DISPLAY_NAME,
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
)
