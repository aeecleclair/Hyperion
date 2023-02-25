from datetime import datetime

from pydantic import BaseModel, Field


class AdvertiserBase(BaseModel):
    name: str
    group_manager_id: str = Field(
        description="The group manager id should by a group identifier"
    )

    class Config:
        orm_mode = True


class AdvertiserComplete(AdvertiserBase):
    id: str


class AdvertiserUpdate(BaseModel):
    name: str | None = None
    group_manager_id: str | None = None


class AdvertBase(BaseModel):
    name: str
    content: str
    advertiser_id: str
    co_advertisers_id: list[str] | None = None
    tags: list[str] | None = None


class AdvertComplete(AdvertBase):
    id: str
    advertiser: AdvertiserComplete
    date: datetime | None = None


class AdvertUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    groups_id: list[str] | None = None
    tags: list[str] | None = None


class TagBase(BaseModel):
    name: str | None = None
    color: str | None = None
    group_manager_id: str = Field(
        description="The group manager id should by a group identifier"
    )


class TagComplete(TagBase):
    id: str


class TagUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    groups_id: list[str] | None = None
    tags: list[str] | None = None
