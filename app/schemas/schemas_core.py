"""Commun schemas file for endpoint /users et /groups because it would cause circular import"""

from datetime import date, datetime

from pydantic import BaseModel, validator

from app.utils import validators
from app.utils.examples import examples_core
from app.utils.types.groups_type import AccountType


class CoreUserBase(BaseModel):
    """Base schema for user's model"""

    name: str
    firstname: str
    nickname: str | None = None


class CoreGroupBase(BaseModel):
    """Base schema for group's model"""

    name: str
    description: str | None = None


class CoreUserSimple(CoreUserBase):
    """Simplified schema for user's model, used when getting all users"""

    id: str

    class Config:
        orm_mode = True


class CoreGroupSimple(CoreGroupBase):
    """Simplified schema for group's model, used when getting all groups"""

    id: str

    class Config:
        orm_mode = True


class CoreUser(CoreUserSimple):
    """Schema for user's model similar to core_user table in database"""

    email: str
    birthday: date | None = None
    promo: int | None = None
    floor: str
    created_on: datetime | None = None
    groups: list[CoreGroupSimple] = []


class CoreUserUpdate(BaseModel):
    """Schema for user update"""

    name: str | None = None
    firstname: str | None = None
    nickname: str | None = None
    birthday: date | None = None
    promo: int | None = None
    floor: str | None = None

    class Config:
        schema_extra = examples_core.example_CoreUserUpdate


class CoreUserCreateRequest(BaseModel):
    """
    The schema is used to send an account creation request.
    **password** is optional as it can either be provided during the creation or the activation
    """

    email: str
    password: str | None = None

    # Password validator
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_password = validator("password", allow_reuse=True)(
        validators.password_validator
    )

    class Config:
        orm_mode = True

        schema_extra = examples_core.example_CoreUserCreateRequest


class CoreBatchUserCreateRequest(BaseModel):
    """
    The schema is used for batch account creation requests. An account type should be provided
    """

    email: str
    account_type: AccountType

    class Config:
        orm_mode = True

        schema_extra = examples_core.example_CoreBatchUserCreateRequest


class CoreUserActivateRequest(CoreUserBase):
    activation_token: str
    password: str | None = None
    birthday: date | None = None
    phone: str | None = None
    promo: int | None = None
    floor: str

    # Password validator
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_password = validator("password", allow_reuse=True)(
        validators.password_validator
    )

    class Config:
        orm_mode = True

        schema_extra = examples_core.example_CoreUserActivateRequest


class CoreGroup(CoreGroupSimple):
    """Schema for group's model similar to core_group table in database"""

    members: list[CoreUserSimple] = []


class CoreGroupCreate(CoreGroupBase):
    """Model for group creation schema"""

    pass


class CoreGroupInDB(CoreGroupBase):
    """Schema for user activation"""

    id: str

    class Config:
        orm_mode = True


class CoreGroupUpdate(BaseModel):
    """Schema for group update"""

    name: str | None = None
    description: str | None = None


class CoreUserRecoverRequest(BaseModel):
    email: str
    user_id: str
    reset_token: str
    created_on: datetime
    expire_on: datetime

    class Config:
        orm_mode = True


class ChangePasswordRequest(BaseModel):
    user_id: str
    old_password: str
    new_password: str

    # Password validator
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_password = validator("new_password", allow_reuse=True)(
        validators.password_validator
    )


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str

    # Password validator
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_password = validator("new_password", allow_reuse=True)(
        validators.password_validator
    )


class CoreMembership(BaseModel):
    """Schema for membership creation (allows to add a user to a group)"""

    user_id: str
    group_id: str
