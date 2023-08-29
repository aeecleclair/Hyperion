from datetime import datetime

from pydantic import BaseModel, Field


class AdvertiserBase(BaseModel):
    name: str
    group_manager_id: str = Field(
        description="The group manager id should be a group identifier"
    )


class AdvertiserComplete(AdvertiserBase):
    id: str

    class Config:
        orm_mode = True


class AdvertiserUpdate(BaseModel):
    name: str | None = None
    group_manager_id: str | None = None


class AdvertBase(BaseModel):
    title: str
    content: str
    advertiser_id: str
    tags: str | None = None


class AdvertComplete(AdvertBase):
    id: str
    date: datetime | None = None

    class Config:
        orm_mode = True


class AdvertReturnComplete(AdvertBase):
    id: str
    advertiser: AdvertiserComplete
    date: datetime | None = None

    class Config:
        orm_mode = True


class AdvertUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: str | None = None
