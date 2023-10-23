from datetime import date

from pydantic import BaseModel


# Schema de base. Contiens toutes les données communes à tous les schemas
class TodosItemBase(BaseModel):
    name: str
    deadline: date | None = None
    done: bool = False

    # Required later to initiate schema using models
    class Config:
        orm_mode = True


# Format des données présente dans la base de donnée
class TodosItemComplete(TodosItemBase):
    id: str
    user_id: str
    creation: date
