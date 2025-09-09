from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdvertBase(BaseModel):
    title: str
    content: str
    advertiser_id: UUID
    post_to_feed: bool = Field(
        default=False,
        description="If the advert should be posted in the feed. It will be pending validation be admin",
    )
    notification: bool


class AdvertComplete(AdvertBase):
    id: UUID
    date: datetime | None = None


class AdvertUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
