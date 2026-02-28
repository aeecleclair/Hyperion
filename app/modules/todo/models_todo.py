from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.types.sqlalchemy import Base, PrimaryKey


class Todo(Base):
    __tablename__ = "todo"

    id: Mapped[PrimaryKey]
    description: Mapped[str]
    done: Mapped[bool]
    user_id: Mapped[str] = mapped_column(ForeignKey("core_user.id"))
