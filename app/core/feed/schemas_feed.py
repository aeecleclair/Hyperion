from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.feed.types_feed import NewsStatus


class News(BaseModel):
    id: UUID
    title: str

    start: datetime
    end: datetime | None

    entity: str = Field(description="Name of the entity that created the news")

    location: str | None = Field(
        description="The news may be related to a specific location",
    )

    action_start: datetime | None = Field(
        description="The news may be related to a specific action. If so, the action button should be displayed at this datetime",
    )

    module: str
    # UUID of the related object in the module database
    module_object_id: UUID

    status: NewsStatus


class NewsComplete(News):
    image_directory: str
    image_id: UUID
