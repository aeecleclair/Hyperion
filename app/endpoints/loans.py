import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_loans
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.models import models_core, models_loan
from app.schemas import schemas_loans
from app.utils.tools import (
    is_group_id_valid,
    is_user_id_valid,
    is_user_member_of_an_allowed_group,
)
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/loans/loaners/",
    response_model=list[schemas_loans.Loaner],
    status_code=200,
    tags=[Tags.loans],
)
async def read_loaners(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new loaner

    **This endpoint is only usable by administrators**
    """

    return await cruds_loans.get_loaners(db=db)


@router.post(
    "/loans/loaners/",
    response_model=schemas_loans.Loaner,
    status_code=201,
    tags=[Tags.loans],
)
async def create_loaner(
    loaner: schemas_loans.LoanerBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new loaner

    **This endpoint is only usable by administrators**
    """

    # We need to check that loaner.group_manager_id is a valid group
    if not await is_group_id_valid(loaner.group_manager_id, db=db):
        raise HTTPException(
            status_code=400,
            detail="Invalid id, group_manager_id must be a valid group id",
        )

    try:
        loaner_db = models_loan.Loaner(
            id=str(uuid.uuid4()),
            name=loaner.name,
            group_manager_id=loaner.group_manager_id,
        )

        return await cruds_loans.create_loaner(loaner=loaner_db, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# TODO: readd this after making sure all information were deleted
# @router.delete(
#    "/loans/loaners/{loaner_id}",
#    status_code=204,
#    tags=[Tags.loans],
# )
# async def delete_loaner(loaner_id: str, db: AsyncSession = Depends(get_db), user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin))):
#


@router.patch(
    "/loans/loaners/{loaner_id}",
    response_model=schemas_loans.LoanerBase,
    status_code=200,
    tags=[Tags.loans],
)
async def update_loaner(
    loaner_id: str,
    loaner_update: schemas_loans.LoanerBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Update a loaner, the request should contain a JSON with the fields to change (not necessarily all fields) and their new value

    **This endpoint is only usable by administrators**
    """

    await cruds_loans.update_loaner(
        loaner_id=loaner_id, loaner_update=loaner_update, db=db
    )

    return loaner_update


@router.get(
    "/loans/loaners/{loaner_id}/loans",
    response_model=list[schemas_loans.Loan],
    status_code=200,
    tags=[Tags.loans],
)
async def get_loans_by_loaner(
    loaner_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all loans from a given group

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loans.get_loaner_by_id(
        loaner_id=loaner_id, db=db
    )
    if loaner is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loaner_id",
        )
    # The user should be a member of the loaner's manager group
    if not is_user_member_of_an_allowed_group(user, [loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loaner_id} loaner",
        )
    return await cruds_loans.get_loans_by_loaner_id(loaner_id=loaner_id, db=db)


@router.get(
    "/loans/loaners/{loaner_id}/items",
    response_model=list[schemas_loans.LoanerItemInDB],
    status_code=200,
    tags=[Tags.loans],
)
async def get_items_by_loaner(
    loaner_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all item of a group from database as a list of dictionaries

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loans.get_loaner_by_id(
        loaner_id=loaner_id, db=db
    )
    if loaner is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loaner_id",
        )
    # The user should be a member of the loaner's manager group
    if not is_user_member_of_an_allowed_group(user, [loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loaner_id} loaner",
        )

    return loaner.items


@router.post(
    "/loans/loaners/{loaner_id}/items",
    response_model=schemas_loans.LoanerItemInDB,
    status_code=200,
    tags=[Tags.loans],
)
async def create_items_for_loaner(
    loaner_id: str,
    item: schemas_loans.LoanerItemBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a new item for a loaner

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loans.get_loaner_by_id(
        loaner_id=loaner_id, db=db
    )
    if loaner is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loaner_id",
        )
    # The user should be a member of the loaner's manager group
    if not is_user_member_of_an_allowed_group(user, [loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loaner_id} loaner",
        )

    loaner_item_db = models_loan.LoanerItem(
        id=str(uuid.uuid4()),
        name=item.name,
        loaner_id=loaner_id,
        suggested_caution=item.suggested_caution,
        multiple=item.multiple,
        suggested_lending_duration=item.suggested_lending_duration,
        available=True,
    )

    return await cruds_loans.create_item(item=loaner_item_db, db=db)


@router.patch(
    "/loans/loaners/{loaner_id}/items/{item_id}",
    response_model=schemas_loans.LoanerItemBase,
    status_code=200,
    tags=[Tags.loans],
)
async def update_items_for_loaner(
    loaner_id: str,
    item_id: str,
    item_update: schemas_loans.LoanerItemBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a loaner's item

    **The user must be a member of the group to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loans.get_loaner_by_id(
        loaner_id=loaner_id, db=db
    )
    item: models_loan.LoanerItem | None = await cruds_loans.get_loaner_item_by_id(
        loaner_item_id=item_id, db=db
    )
    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid item_id",
        )
    if loaner is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loaner_id",
        )
    if item.loaner_id != loaner_id:
        raise HTTPException(
            status_code=400,
            detail=f"Item {item_id} does not belong to {loaner_id} loaner",
        )
    # The user should be a member of the loaner's manager group
    if not is_user_member_of_an_allowed_group(user, [loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loaner_id} loaner",
        )

    await cruds_loans.update_loaner_item(
        item_id=item_id, item_update=item_update, db=db
    )

    return item_update


# TODO: readd this after making sure all information were deleted
# @router.delete(
#    "/loans/loaners/{loaner_id}/items/{item_id}",
#    status_code=204,
#    tags=[Tags.loans],
# )
# async def delete_loaner_item(loaner_id: str, db: AsyncSession = Depends(get_db), user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin))):
#


# Users management


@router.get(
    "/loans/users/me",
    response_model=list[schemas_loans.Loan],
    status_code=200,
    tags=[Tags.loans],
)
async def get_loans_by_borrowers(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all loans from the current user

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_loans.get_loans_by_borrowers(db=db, borrower_id=user.id)


# @router.get(
#    "/loans/users/{user_id}",
#    response_model=list[schemas_loans.Loan],
#    status_code=200,
#    tags=[Tags.loans],
# )
# async def get_loans_by_borrowers(
#    user_id: str,
#    db: AsyncSession = Depends(get_db),
#    user: models_core.CoreUser = Depends(is_user_a_member),
# ):
#    """Return all loans from database as a list of dictionaries"""
#
#    loans = await cruds_loans.get_loans_by_borrowers(db=db, borrower_id=borrower_id)
#    return loans

# @router.get(
#    "/loans/{loan_id}",
#    response_model=schemas_loans.Loan,
#    status_code=200,
#    tags=[Tags.loans],
# )
# async def read_loan(loan_id: str, db: AsyncSession = Depends(get_db)):
#    """Return loan with id from database as a dictionary"""
#
#    db_loan = await cruds_loans.get_loan_by_id(db=db, loan_id=loan_id)
#    if db_loan is None:
#        raise HTTPException(status_code=404, detail="loan not found")
#    return db_loan


@router.post(
    "/loans/",
    response_model=schemas_loans.LoanCreation,
    status_code=201,
    tags=[Tags.loans],
)
async def create_loan(
    loan_creation: schemas_loans.LoanCreation,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a new loan in database and add the requested items

    **The user must be a member of the group to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loans.get_loaner_by_id(
        loaner_id=loan_creation.loaner_id, db=db
    )
    if loaner is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid loaner_id",
        )
    # The user should be a member of the loaner's manager group
    if not is_user_member_of_an_allowed_group(user, [loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loan_creation.loaner_id} loaner",
        )

    # The borrower id should be a valid user
    if not await is_user_id_valid(user_id=loan_creation.borrower_id, db=db):
        raise HTTPException(
            status_code=400,
            detail="Invalid user_id",
        )

    items: list[models_loan.LoanerItem] = []

    # All item ids should be valid
    for item_id in loan_creation.item_ids:
        item: models_loan.LoanerItem | None = await cruds_loans.get_loaner_item_by_id(
            loaner_item_id=item_id, db=db
        )
        if item is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid item_id {item_id}",
            )
        # If the item can not be borrowed more than one time at the time
        # we need to check it is available
        if not item.multiple:
            if not item.available:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item {item_id} is not available",
                )
        # We make a list of every items to mark them as unavailable later
        items.append(item)

    db_loan = models_loan.Loan(
        id=str(uuid.uuid4()),
        borrower_id=loan_creation.borrower_id,
        loaner_id=loan_creation.loaner_id,
        start=loan_creation.start,
        end=loan_creation.end,
        notes=loan_creation.notes,
        caution=loan_creation.caution,
        returned=False,  # A newly created loan is still not returned
    )

    try:
        return await cruds_loans.create_loan(loan=db_loan, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# @router.delete(
#    "/loans/{loan_id}",
#    response_model=standard_responses.Result,
#    status_code=200,  # 204,
#    tags=[Tags.loans],
# )
# async def delete_loan(
#    loan_id: str,
#    db: AsyncSession = Depends(get_db),
# ):
#    """Delete loan from database by id"""
#
#    await cruds_loans.delete_loan(db=db, loan_id=loan_id)
#
#    return standard_responses.Result(success=True)


# @router.patch(
#    "/loans/{loan_id}",
#    response_model=schemas_loans.Loan,
#    tags=[Tags.loans],
# )
# async def update_loan(
#    loan_id: str,
#    loan_update: schemas_loans.Loan,
#    db: AsyncSession = Depends(get_db),
# ):
#    """Update a loan, the request should contain a JSON with the fields to change (not necessarily all fields) and their new value"""
#    loan = await cruds_loans.get_loan_by_id(db=db, loan_id=loan_id)
#    if not loan:
#        raise HTTPException(status_code=404, detail="loan not found")
#
#    await cruds_loans.update_loan(db=db, loan_id=loan_id, loan_update=loan_update)
#
#    return loan


# @router.patch(
#     "/loans/return/{loan_id}",
#     response_model=schemas_loans.Loan,
#     tags=[Tags.loans],
# )
# async def return_loan(
#     loan_id: str,
#     db: AsyncSession = Depends(get_db),
# ):
#     loan = await cruds_loans.get_loan_by_id(db=db, loan_id=loan_id)
#     if not loan:
#         raise HTTPException(status_code=404, detail="loan not found")

#     await cruds_loans.return_loan(db=db, loan_id=loan_id)

#     return loan


#

#

#

#


##


# ===============================================================

# =====================================================


# @router.get(
#     "/loans/history/{group_id}",
#     response_model=list[schemas_loans.Loan],
#     status_code=200,
#     tags=[Tags.loans],
# )
# async def get_history(group_id: str, db: AsyncSession = Depends(get_db)):
#     """Return all returned loans from database as a list of dictionaries"""
#     return await cruds_loans.get_history(db, group_id=group_id)
