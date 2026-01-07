from pydantic import BaseModel

from app.core.groups.groups_type import AccountType


class CoreGroupPermission(BaseModel):
    permission_name: str
    group_id: str


class CoreAccountTypePermission(BaseModel):
    permission_name: str
    account_type: AccountType


class CorePermission(BaseModel):
    permission_name: str
    groups: list[str]
    account_types: list[AccountType]
