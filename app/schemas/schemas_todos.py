from datetime import datetime

from pydantic import BaseModel


class TodosItemBase(BaseModel):
    user_id: str
    name: str
    deadline: datetime | None = None

    class Config:
        orm_mode = True


class TodosItemInDB(TodosItemBase):
    todo_id: str
    creation_time: datetime
