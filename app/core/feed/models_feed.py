from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Mapped

from app.core.feed.types_feed import NewsStatus
from app.types.sqlalchemy import Base, PrimaryKey


class News(Base):
    __tablename__ = "feed_news"

    id: Mapped[PrimaryKey]
    title: Mapped[str]

    start: Mapped[datetime]
    end: Mapped[datetime | None]

    # Name of the entity that created the news
    entity: Mapped[str]

    # The news may be related to a specific location
    location: Mapped[str | None]

    # The news may be related to a specific action
    # If so, the action button should be displayed at this datetime
    action_start: Mapped[datetime | None]

    module: Mapped[str]
    # UUID of the related object in the module database
    module_object_id: Mapped[UUID]

    image_directory: Mapped[str]
    image_id: Mapped[UUID]

    status: Mapped[NewsStatus]
