"""Commun schemas file for endpoint /users et /groups because it would cause circular import"""

from datetime import date, datetime

from pydantic import BaseModel, validator

from app.utils.types.account_type import AccountType
from app.core import security


class CoreUserBase(BaseModel):
    """Base schema for user's model"""

    name: str
    firstname: str
    nickname: str = None


class CoreGroupBase(BaseModel):
    """Base schema for group's model"""

    name: str
    description: str = None


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
    birthday: date = None
    promo: int = None
    floor: str
    created_on: datetime = None
    groups: list[CoreGroupSimple] = []

    class Config:
        orm_mode = True


class CoreUserCreateRequest(BaseModel):
    """
    The schema is used to send an account creation request
    **password** is optional as it can either be provided during the creation or the activation
    """

    email: str
    password: str = None
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
    password: str = None
    birthday: date = None
    phone: str = None
    promo: int = None
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
    password_hash: str = None
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
    birthday: date = None
    promo: int = None
    phone: str = None
    floor: str
    created_on: date

    class Config:
        orm_mode = True


class CoreGroup(CoreGroupSimple):
    """Schema for group's model similar to core_group table in database"""

    members: list[CoreUserSimple] = []

    class Config:
        orm_mode = True


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

    name: str = None
    description: str = None


class CoreUserRecoverRequest(BaseModel):
    email: str
    user_id: str
    reset_token: str
    created_on: datetime
    expire_on: datetime

    class Config:
        orm_mode = True


class CoreMembership(BaseModel):
    """Schema for membership creation (allows to add a user to a group)"""

    id_user: str
    id_group: str
