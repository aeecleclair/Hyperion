from pydantic import BaseModel, ConfigDict

from app.core.schemas_core import CoreUserSimple


class ItemBase(BaseModel):
    qr_code_content: str
    title: str
    content: str


class ItemUpdate(BaseModel):
    qr_code_content: str | None = None
    title: str | None = None
    content: str | None = None


class ItemComplete(ItemBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class ItemAdmin(ItemComplete):
    users: list[CoreUserSimple]


class Completion(BaseModel):
    user: CoreUserSimple
    discovered_count: int
    total_count: int
