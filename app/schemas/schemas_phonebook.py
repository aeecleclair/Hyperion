from pydantic import BaseModel

from app.schemas import schemas_core

# REVIEW - ready to be tested


class RoleTags(BaseModel):
    name: str


class MembershipBase(BaseModel):
    user_id: str
    association_id: str
    role_tags: list[str]
    role_name: str
    mandate_year: int


class MembershipComplete(MembershipBase):
    association: schemas_core.CoreGroup

    class config:
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
