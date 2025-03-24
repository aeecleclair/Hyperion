"""
This file is needed in order to have MyECLPay in visibility.
"""

from app.core.groups.groups_type import AccountType
from app.types.module import Module

module = Module(
    root="myeclpay",
    tag="MyECLPay",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)
