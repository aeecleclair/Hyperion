from pydantic import BaseModel

from app.schemas import schemas_core


class RoleTagsReturn(BaseModel):
    tags: list[str]

    class config:
        orm_mode = True


class add_roletag(BaseModel):
    role_tag: str
    membership_id: str

    class config:
        orm_mode = True


class AssociationBase(BaseModel):
    name: str
    kind: str
    description: str | None = None


class AssociationEdit(BaseModel):
    name: str | None
    kind: str | None
    description: str | None
    mandate_year: int | None


class AssociationEditComplete(AssociationEdit):
    id: str

    class Config:
        orm_mode = True


class AssociationComplete(AssociationBase):
    id: str
    mandate_year: int

    class Config:
        orm_mode = True


class MembershipPost(BaseModel):
    user_id: str
    association_id: str
    role_name: str
    role_tags: str | None  # "roletag1;roletag2;..."

    class Config:
        orm_mode = True


class MembershipBase(MembershipPost):
    id: str
    mandate_year: int

    class Config:
        orm_mode = True


class MembershipEdit(BaseModel):
    association_id: str | None
    role_name: str | None
    role_tags: str | None


class MemberBase(schemas_core.CoreUserSimple):
    id: str
    email: str
    phone: str | None = None
    nickname: str
    firstname: str
    name: str
    promo: int

    class Config:
        orm_mode = True


class MemberComplete(MemberBase):
    memberships: list[MembershipBase]

    class Config:
        orm_mode = True


# class Members(schemas_core.CoreUserSimple):
#     name: str
#     nickname: str | None = None
#     firstname: str
#     email: str
#     promo: int

#     class config:
#         orm_mode = True


# class ReturnMembers(BaseModel):
#     members: list[Members]
#     memberships: list[MembershipBase]


class KindsReturn(BaseModel):
    kinds: list[str]
