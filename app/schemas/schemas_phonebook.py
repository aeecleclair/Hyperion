from pydantic import BaseModel

from app.schemas import schemas_core


class Member(schemas_core.CoreUserSimple):
    email: str
    nickname: str | None = None
    firstname: str
    name: str

    class Config:
        orm_mode = True


class AssociationBase(BaseModel):
    name: str
    type: str
    description: str | None = None


class AssociationComplete(BaseModel):
    id: str
    name: str
    type: str
    description: str | None = None


class Role(BaseModel):
    id: str
    name: str


class RoleCreate(BaseModel):
    name: str


class Post(BaseModel):
    association: AssociationComplete
    role: Role


class CompleteMember(BaseModel):
    member: Member
    posts: list[Post]


# class AssociationMemberBase(BaseModel):
#     user_id: str
#     role: str


# class AssociationMemberComplete(AssociationMemberBase):
#     user: schemas_core.CoreUserSimple

#     class Config:
#         orm_mode = True


# class AssociationMemberEdit(BaseModel):
#     role_id: str | None = None
#     association_id: str | None = None
#     user_id: str | None = None


# class AssociationReturn(BaseModel):
#     name: str
#     id: str
#     members: list[AssociationMemberComplete]


# class UserReturn(BaseModel):
#     user: Member
#     roles: list[RoleComplete]
#     associations: list[AssociationComplete]

#     class Config:
#         orm_mode = True
