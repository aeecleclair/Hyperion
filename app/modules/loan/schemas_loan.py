from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.core.core_endpoints import schemas_core


class LoanerBase(BaseModel):
    name: str
    group_manager_id: str = Field(
        description="The group manager id should by a group identifier",
    )
    model_config = ConfigDict(from_attributes=True)


class LoanerUpdate(BaseModel):
    name: str | None = None
    group_manager_id: str | None = None


class Loaner(LoanerBase):
    id: str


class ItemBase(BaseModel):
    """Base schema for item's model"""

    name: str
    suggested_caution: int
    total_quantity: int
    suggested_lending_duration: int = Field(description="duration in seconds")
    model_config = ConfigDict(from_attributes=True)


class ItemUpdate(BaseModel):
    name: str | None = None
    suggested_caution: int | None = None
    total_quantity: int | None = None
    suggested_lending_duration: int | None = Field(
        description="duration in seconds",
        default=None,
    )


class Item(ItemBase):
    id: str
    loaner_id: str
    loaned_quantity: int


class ItemSimple(BaseModel):
    id: str
    name: str
    loaner_id: str


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
    model_config = ConfigDict(from_attributes=True)


class ItemBorrowed(BaseModel):
    """
    A schema used to represent Item in a loan with its quantity in a request by the client
    """

    item_id: str
    quantity: int


class ItemQuantity(BaseModel):
    """
    A schema used to represent Item in a loan with its quantity in a response to the client
    """

    quantity: int
    itemSimple: ItemSimple


class LoanCreation(LoanBase):
    """
    A schema used to create a new loan
    """

    # list with the association item_id / quantity_borrowed
    items_borrowed: list[ItemBorrowed]


class LoanInDBUpdate(BaseModel):
    """
    item_ids are stored in the database using a relationship table (LoanContent).
    As they are not stored in the loan table in the database, we need a schema that does not contain them
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
    When the client asks to update the Loan with a PATCH request, they should be able to change the loan items.
    """

    items_borrowed: list[ItemBorrowed] | None = None


class Loan(LoanBase):
    """
    A complete representation of a Loan which can be sent by the API
    """

    id: str
    returned: bool
    returned_date: date | None
    items_qty: list[ItemQuantity]
    borrower: schemas_core.CoreUserSimple
    loaner: Loaner


class LoanExtend(BaseModel):
    # The client can either provide a new end date or a timedelta to be added to the old end date.
    end: date | None = Field(None, description="A new return date for the Loan")
    duration: int | None = Field(
        None,
        description="The duration by which the loan should be extended in seconds",
    )
