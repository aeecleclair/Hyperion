from pydantic import BaseModel

from app.schemas import schemas_core


class RoleTagsReturn(BaseModel):
    tags: list[str]

    orm_mode = True


class add_roletag(BaseModel):
    role_tag: str
    membership_id: str

    class config:
        orm_mode = True


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
    mandate_year: int

    class Config:
        orm_mode = True


class MembershipBase(BaseModel):
    user_id: str
    association_id: str
    role_name: str
    role_tags: str | None  # "roletag1;roletag2;..."

    class Config:
        orm_mode = True


class MembershipBase2Complete(MembershipBase):
    id: str
    mandate_year: int

    class Config:
        orm_mode = True


class MembershipComplete(MembershipBase):
    association: AssociationComplete
    id: str
    mandate_year: int

    class Config:
        orm_mode = True


class MembershipEdit(BaseModel):
    association_id: str
    role_name: str
    role_tags: str | None


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


class Members(schemas_core.CoreUserSimple):
    name: str
    nickname: str | None = None
    firstname: str
    email: str
    promotion: int

    class config:
        orm_mode = True


class ReturnMembers(BaseModel):
    members: list[Members]
    memberships: list[MembershipComplete]


class KindsReturn(BaseModel):
    kinds: list[str]
