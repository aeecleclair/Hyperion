import uuid
from datetime import datetime

from pydantic import BaseModel


class FeedbackBase(BaseModel):
    content: str


class Feedback(FeedbackBase):
    id: uuid.UUID
    user_id: str
    user_name: str
    creation: datetime
    is_addressed: bool
