from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.types.datetime import TZDateTime


class Recommendation(Base):
    __tablename__ = "recommendation"

    id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    creation: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str | None] = mapped_column(String, nullable=True)

    summary: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
