import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeedbackBase(BaseModel):
    content: str
    user_id: str


class Feedback(FeedbackBase):
    id: uuid.UUID
    creation: datetime
