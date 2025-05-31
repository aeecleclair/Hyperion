from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.loan import models_loan, schemas_loan


async def get_loaners(
    db: AsyncSession,
) -> Sequence[models_loan.Loaner]:
    """Return the loaner with id"""

    result = await db.execute(select(models_loan.Loaner))
    # With the `unique()` call, the function raise an error inviting to add `unique()` to `result`.
    # `unique()` make sure a row can not be present multiple times in the result
    # This may be caused structure of the database with a relationship loop: loaner->loans->items->loaner
    return result.unique().scalars().all()


async def create_loaner(
    loaner: models_loan.Loaner,
    db: AsyncSession,
) -> models_loan.Loaner:
    """Create a new loaner in database and return it"""

    db.add(loaner)
    await db.flush()
    return loaner


async def update_loaner(
    loaner_id: str,
    loaner_update: schemas_loan.LoanerUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_loan.Loaner)
        .where(models_loan.Loaner.id == loaner_id)
        .values(**loaner_update.model_dump(exclude_none=True)),
    )
    await db.flush()


async def get_loaner_by_id(
    loaner_id: str,
    db: AsyncSession,
) -> models_loan.Loaner | None:
    """Return the loaner with id"""

    result = await db.execute(
        select(models_loan.Loaner)
        .where(models_loan.Loaner.id == loaner_id)
        .options(selectinload(models_loan.Loaner.loans)),
    )
    return result.scalars().first()


async def delete_loaner_by_id(
    loaner_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_loan.Loaner).where(models_loan.Loaner.id == loaner_id),
    )
    await db.flush()


async def create_item(
    item: models_loan.Item,
    db: AsyncSession,
) -> models_loan.Item:
    db.add(item)
    await db.flush()
    return item


async def get_loaner_item_by_id(
    loaner_item_id: str,
    db: AsyncSession,
) -> models_loan.Item | None:
    """Return the item with id"""

    result = await db.execute(
        select(models_loan.Item).where(models_loan.Item.id == loaner_item_id),
    )
    return result.scalars().first()


async def get_loaner_item_by_name_and_loaner_id(
    loaner_item_name: str,
    loaner_id: str,
    db: AsyncSession,
) -> models_loan.Item | None:
    """Return the item with id"""

    result = await db.execute(
        select(models_loan.Item).where(
            models_loan.Item.name == loaner_item_name,
            models_loan.Item.loaner_id == loaner_id,
        ),
    )
    return result.scalars().first()


async def update_loaner_item(
    item_id: str,
    item_update: schemas_loan.ItemUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_loan.Item)
        .where(models_loan.Item.id == item_id)
        .values(**item_update.model_dump(exclude_none=True)),
    )
    await db.flush()


async def delete_loaner_items_by_loaner_id(
    loaner_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_loan.Item).where(models_loan.Item.loaner_id == loaner_id),
    )
    await db.flush()


async def delete_loaner_item_by_id(
    item_id: str,
    db: AsyncSession,
):
    await db.execute(delete(models_loan.Item).where(models_loan.Item.id == item_id))
    await db.flush()


async def get_loans_by_borrower(
    db: AsyncSession,
    borrower_id: str,
    returned: bool | None = None,
) -> Sequence[models_loan.Loan]:
    """Return all loans of a borrower from database"""

    query = select(models_loan.Loan).where(models_loan.Loan.borrower_id == borrower_id)
    if returned is not None:
        query = query.filter(models_loan.Loan.returned.is_(returned))

    result = await db.execute(query)
    # With the `unique()` call, the function raise an error inviting to add `unique()` to `result`.
    # `unique()` make sure a row can not be present multiple times in the result
    # This may be caused structure of the database with a relationship loop: loaner->loans->items->loaner
    return result.unique().scalars().all()


async def create_loan(
    db: AsyncSession,
    loan: models_loan.Loan,
) -> models_loan.Loan:
    db.add(loan)
    await db.flush()
    return loan


async def update_loan(
    loan_id: str,
    loan_update: schemas_loan.LoanInDBUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_loan.Loan)
        .where(models_loan.Loan.id == loan_id)
        .values(**loan_update.model_dump(exclude_none=True)),
    )
    await db.flush()


async def update_loan_returned_status(
    loan_id: str,
    db: AsyncSession,
    returned: bool,
    returned_date: datetime,
):
    await db.execute(
        update(models_loan.Loan)
        .where(models_loan.Loan.id == loan_id)
        .values(
            {
                "returned": returned,
                "returned_date": returned_date,
            },
        ),
    )
    await db.flush()


async def get_loan_by_id(
    db: AsyncSession,
    loan_id: str,
) -> models_loan.Loan | None:
    """Return loan with id from database as a dictionary"""

    result = await db.execute(
        select(models_loan.Loan).where(models_loan.Loan.id == loan_id),
    )
    return result.scalars().first()


async def delete_loan_by_id(
    loan_id: str,
    db: AsyncSession,
):
    await db.execute(delete(models_loan.Loan).where(models_loan.Loan.id == loan_id))
    await db.flush()


async def create_loan_content(
    loan_content: models_loan.LoanContent,
    db: AsyncSession,
) -> None:
    """
    Add an item to a loan using a LoanContent row
    """

    db.add(loan_content)
    await db.flush()


async def get_loan_content_by_loan_id_item_id(
    loan_id: str,
    item_id: str,
    db: AsyncSession,
) -> models_loan.LoanContent | None:
    result = await db.execute(
        select(models_loan.LoanContent).where(
            models_loan.LoanContent.loan_id == loan_id
            and models_loan.LoanContent.item_id == item_id,
        ),
    )
    return result.scalars().first()


async def get_loan_contents_by_loan_id(
    loan_id: str,
    db: AsyncSession,
) -> Sequence[models_loan.LoanContent] | None:
    result = await db.execute(
        select(models_loan.LoanContent).where(
            models_loan.LoanContent.loan_id == loan_id,
        ),
    )
    return result.scalars().all()


async def get_loaned_quantity(
    item_id: str,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(func.sum(models_loan.LoanContent.quantity)).where(
            models_loan.LoanContent.loan.has(returned=False)
            & (models_loan.LoanContent.item_id == item_id),
        ),
    )
    qty: int | None = result.scalars().first()
    return qty or 0


async def delete_loan_content_by_loan_id(
    loan_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_loan.LoanContent).where(
            models_loan.LoanContent.loan_id == loan_id,
        ),
    )
    await db.flush()


async def delete_loan_content_by_item_id(
    item_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_loan.LoanContent).where(
            models_loan.LoanContent.item_id == item_id,
        ),
    )
    await db.flush()
