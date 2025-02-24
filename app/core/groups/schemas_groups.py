from pydantic import BaseModel, ConfigDict, field_validator

from app.utils import validators


class CoreGroupBase(BaseModel):
    """Base schema for group's model"""

    name: str
    description: str | None = None

    _normalize_name = field_validator("name")(validators.trailing_spaces_remover)


class CoreGroupSimple(CoreGroupBase):
    """Simplified schema for group's model, used when getting all groups"""

    id: str
    model_config = ConfigDict(from_attributes=True)


class CoreGroup(CoreGroupSimple):
    """Schema for group's model similar to core_group table in database"""

    members: "list[CoreUserSimple]" = []


class CoreGroupCreate(CoreGroupBase):
    """Model for group creation schema"""


class CoreGroupUpdate(BaseModel):
    """Schema for group update"""

    name: str | None = None
    description: str | None = None

    _normalize_name = field_validator("name")(validators.trailing_spaces_remover)


class CoreMembership(BaseModel):
    """Schema for membership creation (allows adding a user to a group)"""

    user_id: str
    group_id: str
    description: str | None = None


class CoreBatchMembership(BaseModel):
    """
    Schema for batch membership creation
    """

    user_emails: list[str]
    group_id: str
    description: str | None = None


class CoreBatchDeleteMembership(BaseModel):
    """
    Schema for batch membership deletion
    """

    group_id: str


class CoreMembershipDelete(BaseModel):
    user_id: str
    group_id: str


from app.core.users.schemas_users import CoreUserSimple  # noqa: E402, TCH001

CoreGroup.model_rebuild()
