import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.schemas_core import CoreUserSimple
from app.modules.cmm.types_cmm import MemeStatus
from app.types.floors_type import FloorsType


class VoteBase(BaseModel):
    meme_id: str
    positive: bool


class Vote(VoteBase):
    user: CoreUserSimple


class VoteComplete(Vote):
    id: uuid.UUID


class Meme(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user: CoreUserSimple
    creation_time: datetime
    vote_score: int
    votes: list[Vote]
    status: MemeStatus


class ShownMeme(BaseModel):
    id: str
    user: CoreUserSimple
    creation_time: datetime
    my_vote: bool | None
    vote_score: int
    status: MemeStatus


class Ban(BaseModel):
    creation_time: datetime
    end_time: datetime | None
    user: CoreUserSimple
    admin: CoreUserSimple


class Score(BaseModel):
    score: int
    position: int


class UserScore(Score):
    user: CoreUserSimple


class PromoScore(Score):
    promo: int


class FloorScore(Score):
    floor: FloorsType
