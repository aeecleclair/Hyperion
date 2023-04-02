from pydantic import BaseModel

from app.schemas import schemas_core


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


class MembershipBase(BaseModel):
    user_id: str
    association_id: str
    role_id: str


class MembershipComplete(MembershipBase):
    association: AssociationComplete
    role: RoleComplete


class Member(schemas_core.CoreUserSimple):
    id: str
    email: str
    nickname: str | None = None
    firstname: str
    name: str

    class Config:
        orm_mode = True


class MemberComplete(Member):
    memberships: list[MembershipComplete]

    class Config:
        orm_mode = True
