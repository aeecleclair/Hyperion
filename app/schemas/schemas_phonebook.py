from pydantic import BaseModel

from app.schemas import schemas_core


class RoleBase(BaseModel):
    name: str


class RoleComplete(RoleBase):
    id: str

    class Config:
        orm_mode = True


class AssociationBase(BaseModel):
    name: str


class AssociationComplete(AssociationBase):
    id: str

    class Config:
        orm_mode = True


class UserReturn(BaseModel):
    user: schemas_core.CoreUserSimple
    roles: list[RoleComplete]
    associations: list[AssociationComplete]

    class Config:
        orm_mode = True


class RequestUserReturn(BaseModel):
    reponse: list[UserReturn]

    class Config:
        orm_mode = True


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
