from datetime import datetime

from pydantic import BaseModel, Field


class AdvertBase(BaseModel):
    name: str
    content: str | None = None
    group_manager_id: str = Field(
        description="The group manager id should be a group identifier"
    )
    groups_id: list[str] = Field(
        description="The groups ids should be a list of group identifier"
    )
    tags: list[str] | None = None


class AdvertComplete(AdvertBase):
    id: str
    date: datetime | None = None


class AdvertUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    groups_id: list[str] = Field(
        description="The groups ids should be a list of group identifier"
    )
    tags: list[str] | None = None
