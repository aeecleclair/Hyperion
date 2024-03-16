from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecommendationBase(BaseModel):
    title: str
    code: str | None = None
    summary: str
    description: str


class Recommendation(RecommendationBase):
    id: str
    creation: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationEdit(BaseModel):
    title: str | None = None
    code: str | None = None
    summary: str | None = None
    description: str | None = None
