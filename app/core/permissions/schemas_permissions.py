from pydantic import BaseModel

from app.core.groups.groups_type import AccountType


class CoreGroupPermission(BaseModel):
    permission_name: str
    group_id: str


class CoreAccountTypePermission(BaseModel):
    permission_name: str
    account_type: AccountType


class CorePermissions(BaseModel):
    group_permissions: list[CoreGroupPermission] = []
    account_type_permissions: list[CoreAccountTypePermission] = []
