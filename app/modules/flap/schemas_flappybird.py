from datetime import datetime

from pydantic import BaseModel


# Schema de base. Contiens toutes les données communes à tous les schemas
class FlappyBirdScoreBase(BaseModel):
    user_id: str
    value: str

    # Required latter to initiate schema using models
    class Config:
        orm_mode = True


# Format des données présente dans la base de donnée
class FlappyBirdScoreInDB(FlappyBirdScoreBase):
    id: str
    creation_time: datetime
