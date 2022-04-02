from pydantic import BaseModel


class CoreGroupBase(BaseModel):
    nom: str
    description: str | None = None


class CoreGroupBase(CoreGroupBase):
    pass


class CoreGroup(CoreGroupBase):
    id: int

    class Config:
        orm_mode = True


class CoreUserBase(BaseModel):
    login: str
    name: str
    firstname: str
    nick: str
    birth: str
    promo: str
    floor: str
    email: str
    created_on: str


class CoreUserCreate(CoreUserBase):
    password: str


class CoreUser(CoreUserBase):
    id: int
    groups: list[CoreGroup] = []

    class Config:
        orm_mode = True
