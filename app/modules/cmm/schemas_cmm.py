import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

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


class Meme(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user: CoreUserSimple
    creation_time: datetime
    vote_score: int
    votes: list[Vote]
    status: MemeStatus


class FullMeme(Meme):
    my_vote: bool
