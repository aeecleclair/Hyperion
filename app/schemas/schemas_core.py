"""Commun schemas file for endpoint /users et /groups because it would cause circular import"""

from datetime import date, datetime

from pydantic import BaseModel, validator

from app.utils.types.account_type import AccountType
from app.core import security


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


class CoreUserCreateRequest(BaseModel):
    """
    The schema is used to send an account creation request
    **password** is optional as it can either be provided during the creation or the activation
    """

    email: str
    password: str | None = None
    account_type: AccountType

    # Password validator
    # https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
    _normalize_password = validator("password", allow_reuse=True)(
        security.password_validator
    )

    class Config:
        orm_mode = True


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
        security.password_validator
    )

    class Config:
        orm_mode = True


class CoreUserUnconfirmedInDB(BaseModel):
    id: str
    email: str
    password_hash: str | None = None
    account_type: AccountType
    activation_token: str
    created_on: datetime
    expire_on: datetime

    class Config:
        orm_mode = True


class CoreUserInDB(CoreUserBase):
    """Schema for user activation"""

    id: str
    email: str
    password_hash: str
    birthday: date | None = None
    promo: int | None = None
    phone: str | None = None
    floor: str
    created_on: date

    class Config:
        orm_mode = True


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
        security.password_validator
    )


class CoreMembership(BaseModel):
    """Schema for membership creation (allows to add a user to a group)"""

    user_id: str
    group_id: str
