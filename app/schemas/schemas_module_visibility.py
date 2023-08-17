from pydantic import BaseModel


class ModuleVisibility(BaseModel):
    root: str
    allowedGroupIds: list[str]

    class Config:
        orm_mode = True
