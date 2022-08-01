from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_loan
from app.schemas import schemas_loans


async def get_loans_by_groups(
    db: AsyncSession, group_id: str
) -> list[models_loan.Loan] | None:
    """Return all loans of a group from database"""

    result = await db.execute(
        select(models_loan.Loan).where(
            models_loan.Item.group.id == group_id
        )  # TODO : check that line it's really weird
    )
    return result.scalars().all()


async def get_loans_by_borrowers(
    db: AsyncSession, borrower_id: str
) -> list[models_loan.Loan] | None:
    """Return all loans of a borrower from database"""

    result = await db.execute(
        select(models_loan.Loan).where(models_loan.Loan.borrower.id == borrower_id)
    )
    return result.scalars().all()


async def get_loan_by_id(db: AsyncSession, loan_id: str) -> models_loan.Loan | None:
    """Return loan with id from database as a dictionary"""

    result = await db.execute(
        select(models_loan.Loan).where(models_loan.Loan.id == loan_id)
    )
    return result.scalars().first()


async def update_loan(db: AsyncSession, loan_id: str, loan_update):
    await db.execute(
        update(models_loan.Loan)
        .where(models_loan.Loan.id == loan_id)
        .values(**loan_update.dict(exclude_none=True))
    )
    await db.commit()


async def return_loan(db: AsyncSession, loan_id: str):
    await db.execute(
        update(models_loan.Loan)
        .where(models_loan.Loan.id == loan_id)
        .values({"returned": True})
    )
    await db.commit()


async def create_loan(
    db: AsyncSession, loan: schemas_loans.LoanInDB
) -> models_loan.Loan:

    db_loan = models_loan.Loan(**loan.dict())
    db.add(db_loan)
    try:
        await db.commit()
        return db_loan
    except IntegrityError:
        await db.rollback()
        raise


async def delete_loan(db: AsyncSession, loan_id: str):
    """Delete a loan from database by id"""

    await db.execute(delete(models_loan.Loan).where(models_loan.Loan.id == loan_id))
    await db.commit()


async def get_items_by_groups(
    db: AsyncSession, group_id: str
) -> list[models_loan.Item]:
    """Return all items of a group from database"""

    result = await db.execute(
        select(models_loan.Item).where(models_loan.Item.group.id == group_id)
    )
    return result.scalars().all()


async def get_item_by_id(db: AsyncSession, item_id: str) -> models_loan.Item | None:
    """Return item with id from database as a dictionary"""

    result = await db.execute(
        select(models_loan.Item).where(models_loan.Item.id == item_id)
    )
    return result.scalars().first()


async def create_item(
    db: AsyncSession, item: schemas_loans.ItemInDB
) -> models_loan.Item:

    db_item = models_loan.Item(**item.dict())
    db.add(db_item)
    try:
        await db.commit()
        return db_item
    except IntegrityError:
        await db.rollback()
        raise


async def delete_item(db: AsyncSession, item_id: str):
    """Delete a loan from database by id"""

    await db.execute(delete(models_loan.Item).where(models_loan.Item.id == item_id))
    await db.commit()


async def get_history(db: AsyncSession, group_id: str) -> list[models_loan.Loan] | None:
    """Return all returned loans of a group from database"""

    result = await db.execute(
        select(models_loan.Loan).where(
            models_loan.Item.group.id == group_id and models_loan.Loan.returned
        )
    )
    return result.scalars().all()
