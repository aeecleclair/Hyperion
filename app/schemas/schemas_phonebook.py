from pydantic import BaseModel

from app.schemas import schemas_core


class AssociationBase(BaseModel):
    name: str
    type: str
    description: str | None = None


class AssociationEdit(BaseModel):
    name: str | None
    type: str | None
    description: str | None


class AssociationEditComplete(AssociationEdit):
    id: str

    class Config:
        orm_mode = True


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


class MembershipBase(BaseModel):
    user_id: str
    association_id: str
    role_id: str

    class Config:
        orm_mode = True


class MembershipComplete(MembershipBase):
    association: AssociationComplete
    role: RoleComplete

    class Config:
        orm_mode = True


class MemberBase(schemas_core.CoreUserSimple):
    id: str
    email: str
    nickname: str | None = None
    firstname: str
    name: str

    class Config:
        orm_mode = True


class MemberComplete(MemberBase):
    memberships: list[MembershipComplete]

    class Config:
        orm_mode = True
