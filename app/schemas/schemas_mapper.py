from pydantic import BaseModel


class RoomBase(BaseModel):
    id : str
    name: str
    group: str

    class Config:
        orm_mode = True


class RoomUpdate(BaseModel):
    name: str | None = None
    group: str | None = None


class RoomAdminBase(BaseModel):
    user_id: str
    room_id: str

    class Config:
        orm_mode = True


class MemberBase(BaseModel):
    user_id: str
    post: str
    group: str


class MemberUpdate(BaseModel):
    user_id: str | None = None
    post: str | None = None
    group: str | None = None


class MemberComplete(MemberBase):
    username: str
    userfirstname: str
    usernickname: str
    matrix_id: str

    class Config:
        orm_mode = True


