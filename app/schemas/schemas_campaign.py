from pydantic import BaseModel

from app.utils.types.campaign_type import ListType


class SectionBase(BaseModel):
    """Base schema for a section of AEECL."""

    name: str
    description: str


class SectionComplete(SectionBase):
    id: str

    class Config:
        orm_mode = True


class ListMember(BaseModel):
    user_id: str
    role: str

    class Config:
        orm_mode = True


class ListBase(BaseModel):
    """Base schema for a list."""

    name: str
    description: str
    type: ListType
    section: str
    members: list[ListMember]

    class Config:
        orm_mode = True


class ListComplete(ListBase):
    id: str


class ListEdit(BaseModel):
    name: str | None = None
    description: str | None = None
    logo_path: str | None = None
    type: ListType | None = None
    section: str | None = None
    members: list[ListMember] | None = None


class VoteBase(BaseModel):
    """Base schema for a vote."""

    list_id: str

    class Config:
        orm_mode = True


class VoteStatus(BaseModel):
    status: bool
