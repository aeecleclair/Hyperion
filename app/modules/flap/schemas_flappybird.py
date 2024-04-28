from datetime import datetime

from pydantic import BaseModel

from app.core.schemas_core import CoreUserSimple


class FlappyBirdScoreBase(BaseModel):
    value: int

    # Required latter to initiate schema using models
    class Config:
        orm_mode = True


class FlappyBirdScoreInDB(FlappyBirdScoreBase):
    id: str
    user_id: str
    user: CoreUserSimple
    creation_time: datetime


class FlappyBirdScoreFeedback(BaseModel):
    value: int
    user: CoreUserSimple
    creation_time: datetime

    # Required latter to initiate schema using models
    class Config:
        orm_mode = True


class FlappyBirdScoreCompleteFeedBack(FlappyBirdScoreFeedback):
    position: int
