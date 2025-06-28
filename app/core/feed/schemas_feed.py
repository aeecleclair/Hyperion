from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.feed.types_feed import NewsStatus


class News(BaseModel):
    id: UUID
    title: str

    start: datetime
    end: datetime | None

    # Name of the entity that created the news
    entity: str

    module: str
    # UUID of the related object in the module database
    module_object_id: UUID

    image_folder: str
    image_id: UUID

    status: NewsStatus
