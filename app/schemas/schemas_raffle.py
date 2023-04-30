"""Schemas file for endpoint /amap"""

from pydantic import BaseModel

from app.schemas.schemas_core import CoreGroupSimple, CoreUserSimple
from app.utils.types.raffle_types import RaffleStatusType


class RaffleBase(BaseModel):
    """Base schema for raffles"""

    name: str
    status: RaffleStatusType | None = None
    description: str | None = None
    group_id: str


class RaffleEdit(BaseModel):
    name: str | None = None
    description: str | None = None


class RaffleSimple(RaffleBase):
    id: str

    class Config:
        orm_mode = True


class RaffleComplete(RaffleSimple):
    group: CoreGroupSimple

    class Config:
        orm_mode = True


class RaffleStats(BaseModel):
    tickets_sold: int
    amount_raised: float


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


class LotSimple(LotBase):
    id: str

    class Config:
        orm_mode = True


class LotComplete(LotBase):
    id: str

    raffle: RaffleComplete

    class Config:
        orm_mode = True


class PackTicketBase(BaseModel):
    price: float
    pack_size: int
    raffle_id: str

    class Config:
        orm_mode = True


class PackTicketEdit(BaseModel):
    raffle_id: str | None = None
    price: float | None = None
    pack_size: int | None = None

    class Config:
        orm_mode = True


class PackTicketSimple(PackTicketBase):
    id: str

    class Config:
        orm_mode = True


class PackTicketComplete(PackTicketSimple):
    raffle: RaffleSimple

    class Config:
        orm_mode = True


class TicketBase(BaseModel):
    pack_id: str
    user_id: str
    winning_lot: str | None = None


class TicketSimple(TicketBase):
    id: str

    class Config:
        orm_mode = True


class TicketComplete(TicketSimple):
    lot: LotSimple | None
    pack_ticket: PackTicketSimple
    user: CoreUserSimple

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
