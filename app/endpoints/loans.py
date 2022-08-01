import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_loans
from app.dependencies import get_db
from app.schemas import schemas_loans
from app.utils.types.tags import Tags

router = APIRouter()

# =============================================================


@router.get(
    "/loans/{group_id}",
    response_model=list[schemas_loans.Loan],
    status_code=200,
    tags=[Tags.loans],
)
async def get_loans_by_groups(group_id: str, db: AsyncSession = Depends(get_db)):
    """Return all loans from database as a list of dictionaries"""

    loans = await cruds_loans.get_loans_by_groups(db=db, group_id=group_id)
    return loans


@router.get(
    "/loans/{borrower_id}",
    response_model=list[schemas_loans.Loan],
    status_code=200,
    tags=[Tags.loans],
)
async def get_loans_by_borrowers(borrower_id: str, db: AsyncSession = Depends(get_db)):
    """Return all loans from database as a list of dictionaries"""

    loans = await cruds_loans.get_loans_by_borrowers(db=db, borrower_id=borrower_id)
    return loans


@router.get(
    "/loans/{loan_id}",
    response_model=schemas_loans.Loan,
    status_code=200,
    tags=[Tags.loans],
)
async def read_loan(loan_id: str, db: AsyncSession = Depends(get_db)):
    """Return loan with id from database as a dictionary"""

    db_loan = await cruds_loans.get_loan_by_id(db=db, loan_id=loan_id)
    if db_loan is None:
        raise HTTPException(status_code=404, detail="loan not found")
    return db_loan


@router.delete(
    "/loans/{loan_id}",
    status_code=204,
    tags=[Tags.loans],
)
async def delete_loan(loan_id: str, db: AsyncSession = Depends(get_db)):
    """Delete loan from database by id"""

    await cruds_loans.delete_loan(db=db, loan_id=loan_id)


@router.patch(
    "/loans/{loan_id}",
    response_model=schemas_loans.Loan,
    tags=[Tags.loans],
)
async def update_loan(
    loan_id: str,
    loan_update: schemas_loans.Loan,
    db: AsyncSession = Depends(get_db),
):
    """Update a loan, the request should contain a JSON with the fields to change (not necessarily all fields) and their new value"""
    loan = await cruds_loans.get_loan_by_id(db=db, loan_id=loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="loan not found")

    await cruds_loans.update_loan(db=db, loan_id=loan_id, loan_update=loan_update)

    return loan


@router.patch(
    "/loans/return/{loan_id}",
    response_model=schemas_loans.Loan,
    tags=[Tags.loans],
)
async def return_loan(
    loan_id: str,
    db: AsyncSession = Depends(get_db),
):
    loan = await cruds_loans.get_loan_by_id(db=db, loan_id=loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="loan not found")

    await cruds_loans.return_loan(db=db, loan_id=loan_id)

    return loan


@router.post(
    "/loans/",
    response_model=schemas_loans.Loan,
    status_code=201,
    tags=[Tags.loans],
)
async def create_loan(loan: schemas_loans.LoanBase, db: AsyncSession = Depends(get_db)):
    """Create a new loan in database and return it as a dictionary"""

    db_loan = schemas_loans.LoanInDB(id=str(uuid.uuid4()), start=0, **loan.dict())
    try:
        return await cruds_loans.create_loan(loan=db_loan, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# ===============================================================


@router.get(
    "/loans/item/{group_id}",
    response_model=list[schemas_loans.Item],
    status_code=200,
    tags=[Tags.loans],
)
async def get_items_by_groups(group_id: str, db: AsyncSession = Depends(get_db)):
    """Return all item of a group from database as a list of dictionaries"""

    items = await cruds_loans.get_items_by_groups(db=db, group_id=group_id)
    return items


@router.get(
    "/loans/item/{item_id}",
    response_model=schemas_loans.Item,
    status_code=200,
    tags=[Tags.loans],
)
async def read_item(item_id: str, db: AsyncSession = Depends(get_db)):
    """Return item with id from database as a dictionary"""

    db_item = await cruds_loans.get_item_by_id(db=db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return db_item


@router.post(
    "/loans/item",
    response_model=schemas_loans.Item,
    status_code=201,
    tags=[Tags.loans],
)
async def create_item(item: schemas_loans.ItemBase, db: AsyncSession = Depends(get_db)):
    """Create a new group in database and return it as a dictionary"""
    db_item = schemas_loans.ItemInDB(id=str(uuid.uuid4()), **item.dict())
    try:
        return await cruds_loans.create_item(db=db, item=db_item)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete(
    "/loans/item/{item_id}",
    status_code=204,
    tags=[Tags.loans],
)
async def delete_item(item_id: str, db: AsyncSession = Depends(get_db)):
    """Delete loan from database by id"""

    await cruds_loans.delete_item(db=db, item_id=item_id)


# =====================================================


@router.get(
    "/loans/history/{group_id}",
    response_model=list[schemas_loans.Loan],
    status_code=200,
    tags=[Tags.loans],
)
async def get_history(group_id: str, db: AsyncSession = Depends(get_db)):
    """Return all returned loans from database as a list of dictionaries"""
    return await cruds_loans.get_history(db, group_id=group_id)
