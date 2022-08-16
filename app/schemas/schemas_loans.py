from datetime import date, timedelta

from pydantic import BaseModel

from app.schemas.schemas_core import CoreGroup, CoreUserSimple


class LoanerBase(BaseModel):
    """Base schema to create a loaner"""

    name: str
    group_manager_id: str

    class Config:
        orm_mode = True


class LoanerUpdate(BaseModel):
    name: str | None = None
    group_manager_id: str | None = None


class Loaner(LoanerBase):
    id: str


class LoanerItemBase(BaseModel):
    """Base schema for item's model"""

    name: str
    suggested_caution: str
    # A multiple item can be lend to multiple persons at the same time
    multiple: bool = False
    suggested_lending_duration: timedelta

    class Config:
        orm_mode = True


class LoanerItemInDB(LoanerItemBase):
    id: str
    loaner_id: str
    available: bool


class LoanerItem(LoanerItemInDB):
    group: CoreGroup


class LoanerItemUpdate(BaseModel):

    name: str | None = None
    suggested_caution: str | None = None
    multiple: bool | None = None
    suggested_lending_duration: timedelta | None = None


class LoanBase(BaseModel):
    """
    Base schema for loan's model
    """

    borrower_id: str
    loaner_id: str
    start: date
    end: date
    notes: str | None = None
    caution: str | None = None

    class Config:
        orm_mode = True


class LoanCreation(LoanBase):
    """
    A schema used to create a new loan
    """

    # These ids will be used to create the corresponding LoanContent associations
    item_ids: list[str]


class Loan(LoanBase):
    """
    A complete representation of a Loan which can be send by the API
    """

    returned: bool
    items: list[LoanerItemInDB]
