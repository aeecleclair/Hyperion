import uuid
from datetime import datetime

from pydantic import BaseModel

from app.core.core_endpoints.schemas_core import CoreUserSimple


class FlappyBirdScoreBase(BaseModel):
    value: int


class FlappyBirdScore(FlappyBirdScoreBase):
    user: CoreUserSimple
    creation_time: datetime


class FlappyBirdScoreInDB(FlappyBirdScore):
    id: uuid.UUID
    user_id: str


class FlappyBirdScoreCompleteFeedBack(FlappyBirdScore):
    """
    A score with its position in the best players leaderboard
    """

    position: int
