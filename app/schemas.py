from pydantic import BaseModel


class Core_groupBase(BaseModel):
    nom: str
    description: str | None = None


class Core_groupBase(Core_groupBase):
    pass


class Core_group(Core_groupBase):
    id: int

    class Config:
        orm_mode = True


class Core_userBase(BaseModel):
    login: str
    name: str
    firstname: str
    nick: str
    birth: str
    promo: str
    floor: str
    email: str
    created_on: str


class Core_userCreate(Core_userBase):
    password: str


class Core_user(Core_userBase):
    id: int
    groups: list[Core_group] = []

    class Config:
        orm_mode = True
