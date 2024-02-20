from pydantic import BaseModel

from app.schemas import schemas_core


class Member(schemas_core.CoreUserSimple):
    id: str
    email: str
    nickname: str | None = None
    firstname: str
    name: str

    class Config:
        orm_mode = True


class AssociationBase(BaseModel):
    name: str
    type: str
    description: str | None = None


class AssociationComplete(AssociationBase):
    id: str

    class Config:
        orm_mode = True


class RoleBase(BaseModel):
    name: str


class RoleComplete(BaseModel):
    id: str

    class Config:
        orm_mode = True
