from uuid import UUID

from pydantic import BaseModel


class AssociationBase(BaseModel):
    name: str
    group_id: str


class Association(AssociationBase):
    id: UUID


class AssociationUpdate(BaseModel):
    name: str | None = None
    group_id: str | None = None
