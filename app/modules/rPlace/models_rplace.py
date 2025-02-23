from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base, PrimaryKey


class Pixel(Base):
    __tablename__ = "pixels"

    id: Mapped[PrimaryKey]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
    color: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
