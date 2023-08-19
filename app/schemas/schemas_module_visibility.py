from pydantic import BaseModel


class ModuleVisibility(BaseModel):
    root: str
    allowed_group_ids: list[str]

    class Config:
        orm_mode = True
