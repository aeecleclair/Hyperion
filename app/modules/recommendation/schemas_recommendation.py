from datetime import datetime

from pydantic import BaseModel


class RecommendationBase(BaseModel):
    title: str
    code: str
    summary: str
    description: str


class Recommendation(RecommendationBase):
    id: str
    creation: datetime

    class Config:
        orm_mode = True


class RecommendationEdit(BaseModel):
    title: str | None = None
    code: str | None = None
    summary: str | None = None
    description: str | None = None
