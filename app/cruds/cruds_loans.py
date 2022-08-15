from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_loan
from app.schemas import schemas_loans


async def create_loaner(
    loaner: models_loan.Loaner,
    db: AsyncSession,
) -> models_loan.Loaner:
    """Create a new loaner in database and return it"""

    db.add(loaner)
    try:
        await db.commit()
        return loaner
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def update_loaner(
    loaner_id: str,
    loaner_update: schemas_loans.LoanerBase,
    db: AsyncSession,
):
    await db.execute(
        update(models_loan.Loaner)
        .where(models_loan.Loaner.id == loaner_id)
        .values(**loaner_update.dict(exclude_none=True))
    )
    await db.commit()


async def get_loaner_by_id(
    loaner_id: str,
    db: AsyncSession,
) -> models_loan.Loaner | None:
    """Return the loaner with id"""

    result = await db.execute(
        select(models_loan.Loaner).where(models_loan.Loaner.id == loaner_id)
    )
    return result.scalars().first()


async def get_loans_by_loaner_id(
    loaner_id: str,
    db: AsyncSession,
) -> list[models_loan.Loan]:
    """Return all loans of a loaner from database"""

    result = await db.execute(
        select(models_loan.Loan).where(models_loan.Loan.loaner_id == loaner_id)
    )
    return result.scalars().all()


async def create_item(
    item: models_loan.LoanerItem,
    db: AsyncSession,
) -> models_loan.LoanerItem:

    db.add(item)
    try:
        await db.commit()
        return item
    except IntegrityError:
        await db.rollback()
        raise


async def get_loaner_item_by_id(
    loaner_item_id: str,
    db: AsyncSession,
) -> models_loan.LoanerItem | None:
    """Return the item with id"""

    result = await db.execute(
        select(models_loan.LoanerItem).where(
            models_loan.LoanerItem.id == loaner_item_id
        )
    )
    return result.scalars().first()


async def update_loaner_item(
    item_id: str,
    item_update: schemas_loans.LoanerItemBase,
    db: AsyncSession,
):
    await db.execute(
        update(models_loan.LoanerItem)
        .where(models_loan.LoanerItem.id == item_id)
        .values(**item_update.dict(exclude_none=True))
    )
    await db.commit()


async def get_loans_by_borrowers(
    db: AsyncSession, borrower_id: str
) -> list[models_loan.Loan]:
    """Return all loans of a borrower from database"""

    result = await db.execute(
        select(models_loan.Loan).where(models_loan.Loan.borrower.id == borrower_id)
    )
    return result.scalars().all()


async def create_loan(
    db: AsyncSession,
    loan: models_loan.Loan,
) -> models_loan.Loan:
    db.add(loan)
    try:
        await db.commit()
        return loan
    except IntegrityError:
        await db.rollback()
        raise


async def get_loan_by_id(db: AsyncSession, loan_id: str) -> models_loan.Loan | None:
    """Return loan with id from database as a dictionary"""

    result = await db.execute(
        select(models_loan.Loan).where(models_loan.Loan.id == loan_id)
    )
    return result.scalars().first()


# async def update_loan(db: AsyncSession, loan_id: str, loan_update: schemas_loans.LoanCreation):
#    await db.execute(
#        update(models_loan.Loan)
#        .where(models_loan.Loan.id == loan_id)
#        .values(**loan_update.dict(exclude_none=True))
#    )
#    await db.commit()


# async def return_loan(db: AsyncSession, loan_id: str):
#     await db.execute(
#         update(models_loan.Loan)
#         .where(models_loan.Loan.id == loan_id)
#         .values({"returned": True})
#     )
#     await db.commit()


# async def delete_loan(db: AsyncSession, loan_id: str):
#     """Delete a loan from database by id"""

#     await db.execute(delete(models_loan.Loan).where(models_loan.Loan.id == loan_id))
#     await db.commit()


# async def get_items_by_groups(
#     db: AsyncSession, group_id: str
# ) -> list[models_loan.LoanerItem]:
#     """Return all items of a group from database"""

#     result = await db.execute(
#         select(models_loan.LoanerItem).where(
#             models_loan.LoanerItem.group.id == group_id
#         )
#     )
#     return result.scalars().all()


# async def get_item_by_id(db: AsyncSession, item_id: str) -> models_loan.Item | None:
#     """Return item with id from database as a dictionary"""

#     result = await db.execute(
#         select(models_loan.Item).where(models_loan.Item.id == item_id)
#     )
#     return result.scalars().first()


# async def delete_item(db: AsyncSession, item_id: str):
#     """Delete a loan from database by id"""

#     await db.execute(delete(models_loan.Item).where(models_loan.Item.id == item_id))
#     await db.commit()


# async def get_history(db: AsyncSession, group_id: str) -> list[models_loan.Loan] | None:
#     """Return all returned loans of a group from database"""

#     result = await db.execute(
#         select(models_loan.Loan).where(
#             models_loan.Item.group.id == group_id and models_loan.Loan.returned
#         )
#     )
#     return result.scalars().all()
