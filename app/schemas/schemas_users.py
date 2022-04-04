from pydantic import BaseModel


class CoreUserBase(BaseModel):
    id: int = None
    login: str
    name: str
    firstname: str

    class Config:
        orm_mode = True


class CoreGroupBase(BaseModel):
    id: int = None
    name: str
    description: str | None = None

    class Config:
        orm_mode = True


class CoreUser(CoreUserBase):
    nick: str
    birth: str
    promo: str
    floor: str
    email: str
    created_on: str
    groups: list[CoreGroupBase] = []

    class Config:
        orm_mode = True


class CoreUserCreate(CoreUserBase):
    password: str
    nick: str
    birth: str
    promo: str
    floor: str
    email: str
    created_on: str


class CoreGroup(CoreGroupBase):
    members: list[CoreUserBase] = []

    class Config:
        orm_mode = True


class CoreGroupCreate(CoreGroupBase):
    pass
