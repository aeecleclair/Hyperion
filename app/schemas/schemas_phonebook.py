from pydantic import BaseModel

from app.schemas import schemas_core


class RoleTagsReturn(BaseModel):
    tags: list[str]

    class config:
        orm_mode = True


class RoleTagsBase(BaseModel):
    role_tag: str
    membership_id: str

    class config:
        orm_mode = True


class AssociationBase(BaseModel):
    name: str
    kind: str
    description: str | None = None


class AssociationComplete(AssociationBase):
    id: str
    mandate_year: int

    class Config:
        orm_mode = True


class AssociationEdit(BaseModel):
    name: str | None
    kind: str | None
    description: str | None
    mandate_year: int | None


class AssociationEditComplete(AssociationEdit):
    id: str

    class Config:
        orm_mode = True


class MembershipBase(BaseModel):
    user_id: str
    association_id: str
    mandate_year: int
    role_name: str
    role_tags: str | None  # "roletag1;roletag2;..."

    class Config:
        orm_mode = True


class MembershipComplete(MembershipBase):
    id: str

    class Config:
        orm_mode = True


class MembershipEdit(BaseModel):
    user_id: str
    association_id: str
    mandate_year: int
    role_name: str | None
    role_tags: str | None


class MemberBase(schemas_core.CoreUserSimple):
    id: str
    email: str
    phone: str | None = None
    nickname: str | None = None
    firstname: str
    name: str
    promo: int | None = None

    class Config:
        orm_mode = True


class MemberComplete(MemberBase):
    memberships: list[MembershipComplete]

    class Config:
        orm_mode = True


class KindsReturn(BaseModel):
    kinds: list[str]
