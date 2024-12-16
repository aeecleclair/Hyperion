import uuid
from datetime import datetime

from fastapi.datastructures import UploadFile
from pydantic import BaseModel

from app.core.schemas_core import CoreUserSimple
from app.modules.cmm.types_cmm import MemeStatus


class VoteBase(BaseModel):
    meme_id: str
    positive: bool


class Vote(VoteBase):
    user: CoreUserSimple
    creation_time: datetime


class VoteComplete(Vote):
    id: uuid.UUID


class MemeBase(BaseModel):
    pass


class Meme(MemeBase):
    # dans les get
    user: CoreUserSimple
    creation_time: datetime
    vote_score: int
    votes: list[Vote]
    status: MemeStatus
