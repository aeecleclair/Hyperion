from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TodosItem(Base):
    __tablename__ = "todos_item"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    creation: Mapped[date] = mapped_column(Date, nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False)
