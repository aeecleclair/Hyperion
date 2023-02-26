from pydantic import BaseModel

from app.schemas import schemas_core
from app.utils.types.campaign_type import ListType


class RoleBase(BaseModel):
    """Base schema for Role in association"""

    name: str


class RoleComplete(RoleBase):
    id: str

    class Config:
        orm_mode = True


class AssociationBase(BaseModel):
    """Base schema for  association"""

    name: str


class AssociationComplete(RoleBase):
    id: str

    class Config:
        orm_mode = True


class RequestUserReturn(BaseModel):
    user: schemas_core.CoreUserSimple
    id: str
    roles: list[RoleComplete]
    associations: list[AssociationComplete]


class RoleReturn(BaseModel):
    name: str
    id: str

    class Config:
        orm_mode = True


class AssociationMemberBase(BaseModel):
    user_id: str
    role: str

    class Config:
        orm_mode = True


class AssociationMemberComplete(AssociationMemberBase):
    user: schemas_core.CoreUserSimple

    class Config:
        orm_mode = True


class AssociationMembersBase(BaseModel):
    """Base schema for a list."""

    name: str
    type: ListType
    members: list[AssociationMemberBase]


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
