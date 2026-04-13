from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base


class Session(Base):
    __tablename__ = "cinema_session"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    start: Mapped[datetime]
    duration: Mapped[int]
    overview: Mapped[str | None]
    genre: Mapped[str | None]
    year: Mapped[str | None]
