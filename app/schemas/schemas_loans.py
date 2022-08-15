from datetime import date

from pydantic import BaseModel

from app.schemas.schemas_core import CoreGroup, CoreUserSimple


class LoanerBase(BaseModel):
    """Base schema to create a loaner"""

    name: str
    group_manager_id: str

    class Config:
        orm_mode = True


class LoanerInDB(LoanerBase):
    id: str


class ItemBase(BaseModel):
    """Base schema for item's model"""

    name: str
    caution: str
    group_id: str
    expiration: date | None = None


class ItemInDB(ItemBase):

    id: str


class Item(ItemInDB):

    group: CoreGroup

    class Config:
        orm_mode = True


class LoanBase(BaseModel):
    """Base schema for loan's model"""

    borrower_id: str
    item: Item
    notes: str | None = None
    caution: bool | None = None


class LoanInDB(LoanBase):

    start: date
    end: date
    id: str


class Loan(LoanInDB):
    borrower: CoreUserSimple
    item: Item  # TODO change in list[Item] = []

    class Config:
        orm_mode = True
