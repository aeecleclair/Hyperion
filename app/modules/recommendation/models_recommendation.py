from datetime import datetime

from sqlalchemy.orm import Mapped, MappedAsDataclass

from app.types.sqlalchemy import Base, PrimaryKey


class Recommendation(MappedAsDataclass, Base):
    __tablename__ = "recommendation"

    id: Mapped[PrimaryKey]
    creation: Mapped[datetime]
    title: Mapped[str]
    code: Mapped[str | None]
    summary: Mapped[str]
    description: Mapped[str]
