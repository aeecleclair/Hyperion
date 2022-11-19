from datetime import date

from sqlalchemy import Boolean, Column, Date, String

from app.database import Base


class TodosItem(Base):
    __tablename__ = "todos_item"

    id: str = Column(String, primary_key=True, index=True)
    user_id: str = Column(String, index=True, nullable=False)
    name: str = Column(String, nullable=False)
    creation: date = Column(Date, nullable=False)
    deadline: date | None = Column(Date)
    done: bool = Column(Boolean, nullable=False)
