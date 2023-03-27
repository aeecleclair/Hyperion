"""Schemas file for endpoint /amap"""

from pydantic import BaseModel

from app.schemas.schemas_core import CoreUserSimple
from app.utils.types.raffle_types import RaffleStatusType


class RaffleBase(BaseModel):
    """Base schema for raffles"""

    name: str
    status: RaffleStatusType
    description: str | None = None


class RaffleEdit(BaseModel):
    name: str | None = None
    status: RaffleStatusType | None = None
    description: str | None = None


class RaffleSimple(RaffleBase):
    group_id: str


class RaffleComplete(RaffleSimple):
    id: str

    class Config:
        orm_mode = True


# class UserBase(BaseModel):
#     name: str
#     surname: str
#     email: str
#     nb_tickets_bought: int
#     year: int


# class UserComplete(UserBase):
#     id: int


# class WinnerComplete(UserComplete):
#     user: UserComplete
#     lot: str

#     class Config:
#         orm_mode = True


class LotBase(BaseModel):
    name: str
    description: str
    raffle_id: str
    quantity: int

    class Config:
        orm_mode = True


class LotEdit(BaseModel):
    raffle_id: str | None = None
    description: str | None = None
    name: str | None = None
    quantity: int | None = None

    class Config:
        orm_mode = True


class LotComplete(LotBase):
    id: str

    class Config:
        orm_mode = True


class TypeTicketBase(BaseModel):
    price: float
    value: int
    raffle_id: str

    class Config:
        orm_mode = True


class TypeTicketEdit(BaseModel):
    raffle_id: str | None = None
    price: float | None = None
    value: int | None = None

    class Config:
        orm_mode = True


class TypeTicketComplete(TypeTicketBase):
    id: str

    class Config:
        orm_mode = True


class TicketBase(BaseModel):
    type_id: str
    user_id: str
    winning_lot: LotComplete | None = None


class TicketComplete(TicketBase):
    id: str

    class Config:
        orm_mode = True


class CashBase(BaseModel):
    balance: float
    user_id: str

    class Config:
        orm_mode = True


class CashComplete(CashBase):
    user: CoreUserSimple


class CashDB(CashBase):
    user_id: str


class CashEdit(BaseModel):
    balance: float
