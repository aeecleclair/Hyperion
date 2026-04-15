import uuid
from datetime import datetime

from pydantic import BaseModel


class FeedbackBase(BaseModel):
    content: str


class Feedback(FeedbackBase):
    user_id: str
    id: uuid.UUID
    creation: datetime
