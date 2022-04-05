"""Commun schemas file for endpoint /users et /groups because it would cause circular import"""

from datetime import date, datetime
from pydantic import BaseModel


class CoreUserBase(BaseModel):
    name: str
    firstname: str
    nickname: str = None


class CoreGroupBase(BaseModel):
    name: str
    description: str | None = None


class CoreUserSimple(CoreUserBase):
    id: int

    class Config:
        orm_mode = True


class CoreGroupSimple(CoreGroupBase):
    id: int

    class Config:
        orm_mode = True


class CoreUser(CoreUserSimple):
    email: str
    birthday: date = None
    promo: int = None
    floor: str
    created_on: datetime = None
    groups: list[CoreGroupSimple] = []

    class Config:
        orm_mode = True


class CoreUserCreate(CoreUserBase):
    email: str
    password: str
    birthday: date = None
    promo: int = None
    floor: str
    created_on: datetime = None


class CoreGroup(CoreGroupSimple):
    members: list[CoreUserSimple] = []

    class Config:
        orm_mode = True


class CoreGroupCreate(CoreGroupBase):
    pass
