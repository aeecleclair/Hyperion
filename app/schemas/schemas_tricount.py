from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.schemas_core import CoreUserSimple


class TransactionBase(BaseModel):
    sharer_group_id: str
    amount: float
    type: str
    title: str
    description: str | None = None
    update_datetime: datetime
    creator_id: str
    payer_id: str


class TransactionCreate(TransactionBase):
    beneficiaries_user_ids: list[str]


class Transaction(TransactionBase):
    id: str
    creation_datetime: datetime
    beneficiaries: list[CoreUserSimple]

    class Config:
        orm_mode = True


class TransactionUpdateBase(BaseModel):
    amount: float | None = None
    type: str | None = None
    title: str | None = None
    description: str | None = None
    payer_id: str | None = None


class TransactionUpdate(TransactionUpdateBase):
    beneficiaries_user_ids: list[str] | None = None


class Balance(BaseModel):
    user_id: str
    amount: float

    class Config:
        orm_mode = True


class SharerGroupBase(BaseModel):
    name: str


class SharerGroup(SharerGroupBase):
    id: str
    name: str
    members: list[CoreUserSimple]
    transactions: list[Transaction]
    total: float
    balances: list[Balance]

    class Config:
        orm_mode = True


class SharerGroupUpdate(BaseModel):
    name: str | None = None


class SharerGroupMembership(BaseModel):
    user_id: str
    sharer_group_id: str
    # We let the user choose in what order they want to see the sharer groups using `rank`
    position: int = Field(
        description="A SharerGroupMembership with a rank of 0 will be displayed first, then 1, then 2"
    )
    active: bool = Field(
        description="If a membership is inactive, the user should not be allowed to edit the sharergroup"
    )

    class Config:
        orm_mode = True
