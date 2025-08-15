from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdvertiserBase(BaseModel):
    name: str
    group_manager_id: str = Field(
        description="The group manager id should be a group identifier",
    )


class AdvertiserComplete(AdvertiserBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class AdvertiserUpdate(BaseModel):
    name: str | None = None
    group_manager_id: str | None = None


class AdvertBase(BaseModel):
    title: str
    content: str
    advertiser_id: str
    post_to_feed: bool = Field(
        default=False,
        description="If the advert should be posted in the feed. It will be pending validation be admin",
    )


class AdvertComplete(AdvertBase):
    id: str
    date: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class AdvertReturnComplete(AdvertBase):
    id: str
    advertiser: AdvertiserComplete
    date: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class AdvertUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
