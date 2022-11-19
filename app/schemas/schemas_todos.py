from datetime import date

from pydantic import BaseModel


class TodosItemBase(BaseModel):
    name: str
    deadline: date | None = None
    done: bool = False

    class Config:
        orm_mode = True


class TodosItemComplete(TodosItemBase):
    id: str
    user_id: str
    creation: date
