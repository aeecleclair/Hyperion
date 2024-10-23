from datetime import datetime

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from app.types.sqlalchemy import Base, TZDateTime


class Session(MappedAsDataclass, Base):
    __tablename__ = "cinema_session"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    start: Mapped[datetime]
    duration: Mapped[int]
    overview: Mapped[str | None]
    genre: Mapped[str | None]
    tagline: Mapped[str | None]
