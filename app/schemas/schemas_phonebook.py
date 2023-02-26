from pydantic import BaseModel

from app.schemas import schemas_core


class Member(schemas_core.CoreUserSimple):
    email: str


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
    user: Member
    roles: list[RoleComplete]
    associations: list[AssociationComplete]

    class Config:
        orm_mode = True


class RequestUserReturn(BaseModel):
    reponse: list[UserReturn]

    class Config:
        orm_mode = True

    name: str


class AssociationBase(BaseModel):
    """Base schema for  association"""

    name: str


class AssociationComplete(AssociationBase):
    id: str

    class Config:
        orm_mode = True


class RequestUserReturn(BaseModel):
    user: schemas_core.CoreUserSimple
    id: str
    roles: list[RoleComplete]
    associations: list[AssociationComplete]


class AssociationMemberBase(BaseModel):
    user_id: str
    role: str

    class Config:
        orm_mode = True


class AssociationMemberComplete(AssociationMemberBase):
    user: schemas_core.CoreUserSimple

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
