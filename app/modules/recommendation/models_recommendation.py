from datetime import datetime

from sqlalchemy.orm import Mapped

from app.database import Base, pk


class Recommendation(Base):
    __tablename__ = "recommendation"

    id: Mapped[pk]
    creation: Mapped[datetime]
    title: Mapped[str]
    code: Mapped[str | None]
    summary: Mapped[str]
    description: Mapped[str]
