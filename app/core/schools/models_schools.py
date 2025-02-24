from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base, PrimaryKey


class CoreSchool(Base):
    __tablename__ = "core_school"

    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(unique=True)
    email_regex: Mapped[str]
