from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUser, CoreUserSimple


class ThreadBase(BaseModel):
    name: str
    image: str | None
    is_public: bool

    class Config:
        orm_mode = True


class Thread(ThreadBase):
    creation_date: datetime
    id: str
    members: list[CoreUser]
    messages: list[ThreadMessage]

    class Config:
        orm_mode = True


class ThreadMemberBase(BaseModel):
    thread_id: str
    user_id: str

    class Config:
        orm_mode = True


class UserWithPermissions(BaseModel):
    user_id: str
    permissions: int

    class Config:
        orm_mode = True


class ThreadMember(ThreadMemberBase):
    permissions: int
    user: CoreUserSimple

    class Config:
        orm_mode = True


class ThreadMessageBase(BaseModel):
    content: str | None
    image: str | None

    class Config:
        orm_mode = True


class ThreadMessage(ThreadMessageBase):
    author_id: str
    timestamp: datetime
    id: str

    class Config:
        orm_mode = True
