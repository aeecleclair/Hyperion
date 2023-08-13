from datetime import datetime

from pydantic import BaseModel, Field


class AdvertBase(BaseModel):
    name: str
    content: str | None = None
    group_manager_id: str = Field(
        description="The group manager id should be a group identifier"
    )
    groups_id: list[str] | None = None
    tags: list[str] | None = None


class AdvertComplete(AdvertBase):
    id: str
    date: datetime | None = None


class AdvertUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    groups_id: list[str] | None = None
    tags: list[str] | None = None


class TagBase(BaseModel):
    name: str | None = None
    color: str | None = None


class TagComplete(TagBase):
    id: str


class TagUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    groups_id: list[str] | None = None
    tags: list[str] | None = None
