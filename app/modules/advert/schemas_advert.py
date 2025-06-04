from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

class AdvertType(str, Enum):
    EVENT = "event"
    ADVERT = "advert"
    SHOTGUN = "shotgun"
    OTHER = "other"

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
    advert_type: AdvertType
    release_date: datetime # The date when the advert will be released
    start_date: datetime | None # The date when an event starts for example
    end_date: datetime | None # The date when an event ends for example
    tags: str | None = None


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
    tags: str | None = None
    advert_type: AdvertType
    release_date: datetime # The date when the advert will be released
    start_date: datetime | None # The date when an event starts for example
    end_date: datetime | None # The date when an event ends for example
