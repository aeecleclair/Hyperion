from datetime import date

from sqlalchemy import Boolean, Column, Date, ForeignKey, String

from app.database import Base


class TodosItem(Base):
    __tablename__ = "todos_item"

    id: str = Column(String, primary_key=True, index=True)
    user_id: str = Column(ForeignKey("core_user.id"), nullable=False, index=True)
    name: str = Column(String, nullable=False)
    creation: date = Column(Date, nullable=False)
    deadline: date | None = Column(Date)
    done: bool = Column(Boolean, nullable=False)
