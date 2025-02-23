from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base, PrimaryKey


class Pixel(Base):
    __tablename__ = "pixels"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    color: Mapped[str]
    date: Mapped[datetime]
    x: Mapped[int]
    y: Mapped[int]
