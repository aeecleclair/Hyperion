from datetime import datetime

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple


class FlappyBirdScoreBase(BaseModel):
    user_id: str
    value: int

    # Required latter to initiate schema using models
    class Config:
        orm_mode = True


class FlappyBirdScoreInDB(FlappyBirdScoreBase):
    id: str
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
