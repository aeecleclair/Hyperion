from pydantic import BaseModel


class CoreGroupBase(BaseModel):
    nom: str
    description: str | None = None

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

    class Config:
        orm_mode = True


class CoreGroupCreate(CoreGroupBase):
    pass


class CoreGroup(CoreGroupBase):
    id: int
    members: list[CoreUserBase] = []

    class Config:
        orm_mode = True


class CoreUserCreate(CoreUserBase):
    password: str


class CoreUser(CoreUserBase):
    id: int
    groups: list[CoreGroupBase] = []

    class Config:
        orm_mode = True
