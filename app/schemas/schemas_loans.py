from datetime import date, timedelta

from pydantic import BaseModel, Field

from app.schemas.schemas_core import CoreGroup


class LoanerBase(BaseModel):
    name: str
    group_manager_id: str = Field(
        description="The group manager id should by a group identifier"
    )

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
    suggested_caution: int
    # A multiple item can be lend to multiple persons at the same time
    multiple: bool = Field(
        False, description="If the item can be lend to multiple users at the same time"
    )
    suggested_lending_duration: timedelta

    class Config:
        orm_mode = True


class LoanerItemUpdate(BaseModel):

    name: str | None = None
    suggested_caution: int | None = None
    multiple: bool | None = None
    suggested_lending_duration: timedelta | None = None


class LoanerItem(LoanerItemBase):
    id: str
    loaner_id: str
    available: bool


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
    items: list[LoanerItem]
