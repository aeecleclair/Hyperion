from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base


class Advert(Base):
    __tablename__ = "advert_adverts"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    advertiser_id: Mapped[UUID] = mapped_column(
        ForeignKey("associations_associations.id"),
    )
    title: Mapped[str]
    content: Mapped[str]
    date: Mapped[datetime]
    post_to_feed: Mapped[bool]
    notification: Mapped[bool]
