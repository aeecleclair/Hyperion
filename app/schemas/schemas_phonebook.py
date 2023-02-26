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


class AssociationMemberBase(BaseModel):
    user_id: str
    role: str


class AssociationMemberComplete(AssociationMemberBase):
    user: schemas_core.CoreUserSimple

    class Config:
        orm_mode = True


class AssociationMemberEdit(BaseModel):
    role_id: str | None = None
    association_id: str | None = None
    mandate_year: int | None = None


class RoleEdit(BaseModel):
    name: str | None = None


class AssociationEdit(BaseModel):
    name: str | None = None
