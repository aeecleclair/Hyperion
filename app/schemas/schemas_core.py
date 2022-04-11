"""
Commun schemas file for endpoint /users et /groups because it would cause circular import,
used by fastAPI in the endpoints file
"""

from datetime import date, datetime

from pydantic import BaseModel


class CoreUserBase(BaseModel):
    """Base schema for user's model"""

    name: str
    firstname: str
    nickname: str = None


class CoreGroupBase(BaseModel):
    """Base shema for group's model"""

    name: str
    description: str | None = None


class CoreUserSimple(CoreUserBase):
    """Simplified schema for user's model, used when getting all users"""

    id: int

    class Config:
        orm_mode = True


class CoreGroupSimple(CoreGroupBase):
    """Simplified schema for group's model, used when getting all groups"""

    id: int

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


class CoreUserCreate(CoreUserBase):
    """Schema for user creation"""

    email: str
    password: str
    birthday: date = None
    promo: int = None
    floor: str
    created_on: datetime = None


class CoreGroup(CoreGroupSimple):
    """Schema for group's model similar to core_group table in database"""

    members: list[CoreUserSimple] = []

    class Config:
        orm_mode = True


class CoreGroupCreate(CoreGroupBase):
    """Model for group creation schema"""

    pass
