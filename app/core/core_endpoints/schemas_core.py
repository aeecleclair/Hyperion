"""Common schemas file for endpoint /users et /groups because it would cause circular import"""

from pydantic import BaseModel, ConfigDict

from app.core.groups.groups_type import AccountType


class CoreInformation(BaseModel):
    """Information about Hyperion"""

    ready: bool
    version: str
    minimal_titan_version_code: int


class ModuleVisibility(BaseModel):
    root: str
    allowed_group_ids: list[str]
    allowed_account_types: list[AccountType]
    model_config = ConfigDict(from_attributes=True)


class ModuleVisibilityCreate(BaseModel):
    root: str
    allowed_group_id: str | None = None
    allowed_account_type: AccountType | None = None
    model_config = ConfigDict(from_attributes=True)
