from datetime import date

from sqlalchemy.orm import Mapped

from app.types.sqlalchemy import Base, PrimaryKey


class Paper(Base):
    __tablename__ = "ph_papers"

    id: Mapped[PrimaryKey]
    name: Mapped[str]
    release_date: Mapped[date]
