from pydantic import BaseModel, ConfigDict

from app.schemas.schemas_core import CoreUserSimple
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


class RaffleComplete(RaffleBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class RaffleStats(BaseModel):
    tickets_sold: int
    amount_raised: float


class PrizeBase(BaseModel):
    name: str
    description: str
    raffle_id: str
    quantity: int
    model_config = ConfigDict(from_attributes=True)


class PrizeEdit(BaseModel):
    raffle_id: str | None = None
    description: str | None = None
    name: str | None = None
    quantity: int | None = None


class PrizeSimple(PrizeBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class PrizeComplete(PrizeBase):
    id: str
    raffle: RaffleComplete
    model_config = ConfigDict(from_attributes=True)


class PackTicketBase(BaseModel):
    price: float
    pack_size: int
    raffle_id: str
    model_config = ConfigDict(from_attributes=True)


class PackTicketEdit(BaseModel):
    raffle_id: str | None = None
    price: float | None = None
    pack_size: int | None = None
    model_config = ConfigDict(from_attributes=True)


class PackTicketSimple(PackTicketBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class PackTicketComplete(PackTicketSimple):
    raffle: RaffleComplete
    model_config = ConfigDict(from_attributes=True)


class TicketBase(BaseModel):
    pack_id: str
    user_id: str
    winning_prize: str | None = None


class TicketSimple(TicketBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class TicketComplete(TicketSimple):
    prize: PrizeSimple | None = None
    pack_ticket: PackTicketSimple
    user: CoreUserSimple
    model_config = ConfigDict(from_attributes=True)


class CashBase(BaseModel):
    balance: float
    user_id: str
    model_config = ConfigDict(from_attributes=True)


class CashComplete(CashBase):
    user: CoreUserSimple


class CashDB(CashBase):
    user_id: str


class CashEdit(BaseModel):
    balance: float
