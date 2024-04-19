from datetime import datetime

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.types.sqlalchemy import TZDateTime


class Session(Base):
    __tablename__ = "cinema_session"

    id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    start: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    overview: Mapped[str] = mapped_column(String, nullable=True)
    genre: Mapped[str] = mapped_column(String, nullable=True)
    tagline: Mapped[str] = mapped_column(String, nullable=True)
