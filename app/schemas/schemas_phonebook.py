from pydantic import BaseModel

from app.schemas import schemas_core
from app.utils.types.campaign_type import ListType


class RequestUserReturn(BaseModel):
    user: schemas_core.CoreUserSimple
    id: str
    roles: list[str]
    associations: list[str]


class RoleReturn(BaseModel):
    name: str
    id: str

    class Config:
        orm_mode = True


class MemberEdit(BaseModel):
    role_id: str | None = None
    association_id: str | None = None
    mandate_year: int | None = None

    class Config:
        orm_mode = True


class RoleEdit(BaseModel):
    name: str | None = None

    class Config:
        orm_mode = True


class AssociationEdit(BaseModel):
    name: str | None = None

    class Config:
        orm_mode = True
