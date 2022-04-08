"""Commun schemas file for endpoint /users et /groups because it would cause circular import"""

from datetime import date, datetime
from pydantic import BaseModel


class CoreUserBase(BaseModel):
    """Base model for user schema"""

    name: str
    firstname: str
    nickname: str = None


class CoreGroupBase(BaseModel):
    """Base model for group schema"""

    name: str
    description: str | None = None


class CoreUserSimple(CoreUserBase):
    """Simplified model for user schema use for getting all users"""

    id: int

    class Config:
        orm_mode = True


class CoreGroupSimple(CoreGroupBase):
    """Simplified model for group schema use for getting all groups"""

    id: int

    class Config:
        orm_mode = True


class CoreUser(CoreUserSimple):
    """Model for user schema similar to CoreUser table in database"""

    email: str
    birthday: date = None
    promo: int = None
    floor: str
    created_on: datetime = None
    groups: list[CoreGroupSimple] = []

    class Config:
        orm_mode = True


class CoreUserCreate(CoreUserBase):
    """Model for user creation schema"""

    email: str
    password: str
    birthday: date = None
    promo: int = None
    floor: str
    created_on: datetime = None


class CoreGroup(CoreGroupSimple):
    """Model for group schema similar to CoreGroup table in database"""

    members: list[CoreUserSimple] = []

    class Config:
        orm_mode = True


class CoreGroupCreate(CoreGroupBase):
    """Model for group creation schema"""

    pass
