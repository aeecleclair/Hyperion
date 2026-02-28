from uuid import UUID, uuid4

from pydantic import BaseModel


class TodoBase(BaseModel):
    description: str


class Todo(TodoBase):
    id: UUID
    done: bool
    user_id: str


class TodoEdit(TodoBase):
    description: str | None = None
    done: bool | None = None
