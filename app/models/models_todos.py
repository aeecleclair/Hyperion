from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.database import Base


class TodosItem(Base):
    __tablename__ = "todos_item"

    todo_id: str = Column(String, primary_key=True, index=True)
    user_id: str = Column(String, index=True, nullable=False)
    name: str = Column(String, nullable=False)
    deadline: datetime | None = Column(DateTime)
    creation_time: datetime = Column(DateTime, nullable=False)
