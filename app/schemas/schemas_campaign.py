from pydantic import BaseModel

from app.schemas import schemas_core
from app.utils.types.campaign_type import ListType, StatusType


class SectionBase(BaseModel):
    """Base schema for a section of AEECL."""

    name: str
    description: str


class SectionComplete(SectionBase):
    id: str

    class Config:
        orm_mode = True


class ListMemberBase(BaseModel):
    user_id: str
    role: str

    class Config:
        orm_mode = True


class ListMemberComplete(ListMemberBase):
    user: schemas_core.CoreUserSimple

    class Config:
        orm_mode = True


class ListBase(BaseModel):
    """Base schema for a list."""

    name: str
    description: str
    type: ListType
    section_id: str
    members: list[ListMemberBase]


class ListComplete(ListBase):
    id: str

    class Config:
        orm_mode = True


class SectionReturn(BaseModel):
    name: str
    description: str
    id: str
    lists: list[ListComplete]

    class Config:
        orm_mode = True


class ListReturn(BaseModel):
    id: str
    name: str
    description: str
    type: ListType
    section: SectionComplete
    members: list[ListMemberComplete]

    class Config:
        orm_mode = True


class ListEdit(BaseModel):
    name: str | None = None
    description: str | None = None
    type: ListType | None = None
    members: list[ListMemberBase] | None = None


class VoteBase(BaseModel):
    """Base schema for a vote."""

    list_id: str

    class Config:
        orm_mode = True


class VoteStatus(BaseModel):
    status: StatusType

    class Config:
        orm_mode = True


class Result(BaseModel):
    list_id: str
    count: int


class VoteStats(BaseModel):
    section_id: str
    has_voted: int
