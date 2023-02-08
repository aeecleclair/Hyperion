from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ThreadBase(BaseModel):
    name: str
    image: str


class Thread(ThreadBase):
    creation_date: datetime
    id: str
    is_public: bool
    member_ids: list[str]
    messages: list[ThreadMessage]


class ThreadMemberBase(BaseModel):
    thread_id: str
    core_user_id: str


class ThreadMember(ThreadMemberBase):
    id: str
    messages: list[str]


class ThreadMessageBase(BaseModel):
    content: str
    image: str


class ThreadMessage(ThreadMessageBase):
    author_id: str
    timestamp: datetime
    id: str
