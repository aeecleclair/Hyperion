from datetime import date, timedelta

from pydantic import BaseModel, Field

from app.schemas import schemas_core


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


class ItemBase(BaseModel):
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


class ItemUpdate(BaseModel):

    name: str | None = None
    suggested_caution: int | None = None
    multiple: bool | None = None
    suggested_lending_duration: timedelta | None = None


class Item(ItemBase):
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


class LoanInDBUpdate(BaseModel):
    """
    item_ids are stored in the database using a relationship table (LoanContent).
    As they are not stored in the loan table in the database, we need a schema that does not contains them
    for the cruds update_loan function
    """

    borrower_id: str | None = None
    start: date | None = None
    end: date | None = None
    notes: str | None = None
    caution: str | None = None
    returned: bool | None = None


class LoanUpdate(LoanInDBUpdate):
    """
    When the client ask to update the Loan with a PATCH request, they should be able to change the loan items.
    """

    item_ids: list[str] | None = None


class Loan(LoanBase):
    """
    A complete representation of a Loan which can be send by the API
    """

    id: str
    returned: bool
    items: list[Item]
    borrower: schemas_core.CoreUserSimple
    loaner: Loaner


class LoanExtend(BaseModel):

    # The client can either provide a new end date or a timedelta to be added to the old end date.
    end: date | None = Field(None, description="A new return date for the Loan")
    duration: timedelta | None = Field(
        None, description="The duration the loan should be extended of"
    )
