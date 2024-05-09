from datetime import datetime

from pydantic import BaseModel

from app.core.schemas_core import CoreUserSimple


class FlappyBirdScoreBase(BaseModel):
    value: int


class FlappyBirdScoreInDB(FlappyBirdScoreBase):
    id: str
    user_id: str
    user: CoreUserSimple
    creation_time: datetime


class FlappyBirdScoreFeedback(BaseModel):
    value: int
    user: CoreUserSimple
    creation_time: datetime


class FlappyBirdScoreCompleteFeedBack(FlappyBirdScoreFeedback):
    position: int
