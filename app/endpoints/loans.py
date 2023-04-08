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
    Get existing loaners.

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
    Create a new loaner.

    Each loaner is associated with a `manager_group`. Users belonging to this group are able to manage the loaner items and loans.

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


@router.delete(
    "/loans/loaners/{loaner_id}",
    status_code=204,
    tags=[Tags.loans],
)
async def delete_loaner(
    loaner_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Delete a loaner. All items and loans associated with the loaner will also be deleted from the database.

    **This endpoint is only usable by administrators**
    """
    loaner: models_loan.Loaner | None = await cruds_loans.get_loaner_by_id(
        loaner_id=loaner_id, db=db
    )
    if loaner is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loaner_id",
        )

    # We delete all loans associated with this loaner
    for loan in loaner.loans:
        # We first remove LoanContents associated with the loan
        await cruds_loans.delete_loan_content_by_loan_id(loan_id=loan.id, db=db)
        # Then we remove the loan
        await cruds_loans.delete_loan_by_id(loan_id=loan.id, db=db)

    await cruds_loans.delete_loaner_items_by_loaner_id(loaner_id=loaner_id, db=db)
    await cruds_loans.delete_loaner_by_id(loaner_id=loaner_id, db=db)


@router.patch(
    "/loans/loaners/{loaner_id}",
    status_code=204,
    tags=[Tags.loans],
)
async def update_loaner(
    loaner_id: str,
    loaner_update: schemas_loans.LoanerUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Update a loaner, the request should contain a JSON with the fields to change (not necessarily all fields) and their new value.

    **This endpoint is only usable by administrators**
    """

    await cruds_loans.update_loaner(
        loaner_id=loaner_id, loaner_update=loaner_update, db=db
    )


@router.get(
    "/loans/loaners/{loaner_id}/loans",
    response_model=list[schemas_loans.Loan],
    status_code=200,
    tags=[Tags.loans],
)
async def get_loans_by_loaner(
    loaner_id: str,
    returned: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all loans from a given group.


    The query string `returned` can be used to get only return or non returned loans. By default, all loans are returned.


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

    # We didn't manage to use a filter condition in the ORM, as we did for /loans/users/me
    # so we iterate over the list to filter loans based on their returned status
    if returned is not None:
        return [loan for loan in loaner.loans if loan.returned == returned]

    # We use the ORM relationship capabilities to load loans in the loaner object
    return loaner.loans


@router.get(
    "/loans/loaners/{loaner_id}/items",
    response_model=list[schemas_loans.Item],
    status_code=200,
    tags=[Tags.loans],
)
async def get_items_by_loaner(
    loaner_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all items of a loaner.

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

    # We use the ORM relationship capabilities to load items in the loaner object
    return loaner.items


@router.post(
    "/loans/loaners/{loaner_id}/items",
    response_model=schemas_loans.Item,
    status_code=201,
    tags=[Tags.loans],
)
async def create_items_for_loaner(
    loaner_id: str,
    item: schemas_loans.ItemBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a new item for a loaner. A given loaner can not have more than one item with the same `name`.

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

    # We need to check that the loaner does not have another item with the same name
    if (
        await cruds_loans.get_loaner_item_by_name_and_loaner_id(
            loaner_item_name=item.name, loaner_id=loaner_id, db=db
        )
        is not None
    ):
        raise HTTPException(
            status_code=400,
            detail=f"The loaner {loaner_id} has already an item with the name {item.name}",
        )

    try:
        loaner_item_db = models_loan.Item(
            id=str(uuid.uuid4()),
            name=item.name,
            loaner_id=loaner_id,
            suggested_caution=item.suggested_caution,
            total_amount=item.total_amount,
            loaned_amount=0,
            suggested_lending_duration=item.suggested_lending_duration,
        )

        return await cruds_loans.create_item(item=loaner_item_db, db=db)

    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/loans/loaners/{loaner_id}/items/{item_id}",
    status_code=204,
    tags=[Tags.loans],
)
async def update_items_for_loaner(
    loaner_id: str,
    item_id: str,
    item_update: schemas_loans.ItemUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Update a loaner's item.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loans.get_loaner_by_id(
        loaner_id=loaner_id, db=db
    )
    item: models_loan.Item | None = await cruds_loans.get_loaner_item_by_id(
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


@router.delete(
    "/loans/loaners/{loaner_id}/items/{item_id}",
    status_code=204,
    tags=[Tags.loans],
)
async def delete_loaner_item(
    loaner_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a loaner's item.
    This will remove the item from all loans but won't delete any loan.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """
    # We need to make sure the user is allowed to manage the loaner
    item: models_loan.Item | None = await cruds_loans.get_loaner_item_by_id(
        loaner_item_id=item_id, db=db
    )
    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid item_id",
        )
    if item.loaner_id != loaner_id:
        raise HTTPException(
            status_code=400,
            detail=f"Item {item_id} does not belong to {loaner_id} loaner",
        )
    # The user should be a member of the loaner's manager group
    if not is_user_member_of_an_allowed_group(user, [item.loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loaner_id} loaner",
        )

    await cruds_loans.delete_loan_content_by_item_id(item_id=item_id, db=db)
    await cruds_loans.delete_loaner_item_by_id(item_id=item_id, db=db)


@router.get(
    "/loans/users/me",
    response_model=list[schemas_loans.Loan],
    status_code=200,
    tags=[Tags.loans],
)
async def get_current_user_loans(
    returned: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all loans from the current user.

    The query string `returned` can be used to get only returned or non returned loans. By default, all loans are returned.

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_loans.get_loans_by_borrower(
        db=db,
        borrower_id=user.id,
        returned=returned,
    )


@router.get(
    "/loans/users/me/loaners",
    response_model=list[schemas_loans.Loaner],
    status_code=200,
    tags=[Tags.loans],
)
async def get_current_user_loaners(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all loaners the current user can manage.

    **The user must be authenticated to use this endpoint**
    """

    user_loaners: list[models_loan.Loaner] = []

    existing_loaners: list[models_loan.Loaner] = await cruds_loans.get_loaners(db=db)

    for loaner in existing_loaners:
        if is_user_member_of_an_allowed_group(
            allowed_groups=[loaner.group_manager_id],
            user=user,
        ):
            user_loaners.append(loaner)

    return user_loaners


@router.post(
    "/loans/",
    response_model=schemas_loans.Loan,
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

    **The user must be a member of the loaner group_manager to use this endpoint**
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

    # list of item and amount_borrowed
    items: list[tuple[models_loan.Item, int]] = []

    # All items should be valid, available and belong to the loaner
    for item_borrowed in loan_creation.items_borrowed:
        item_id: str = item_borrowed.item_id
        amount_borrowed: int = item_borrowed.amount_borrowed

        item: models_loan.Item | None = await cruds_loans.get_loaner_item_by_id(
            loaner_item_id=item_id, db=db
        )
        if item is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid item_id {item_id}",
            )
        # We check the item belong to the loaner
        if item.loaner_id != loan_creation.loaner_id:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item_id} does not belong to {loan_creation.loaner_id} loaner",
            )

        # We need to check if the amount is available
        available_amount: int = item.total_amount - item.loaned_amount
        isLoanedAmountPossible = amount_borrowed <= available_amount
        if not isLoanedAmountPossible:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item_id} is not available",
            )
        # We make a list of every new item with the amount borrowed to update the loaned amount and create the loaned content
        item.loaned_amount += amount_borrowed
        items.append((item, amount_borrowed))

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
        await cruds_loans.create_loan(loan=db_loan, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    for item, amount_borrowed in items:
        # We update in db the loaned amount for each item
        await cruds_loans.update_loaner_item_loaned_amount(
            item_id=item.id, loaned_amount=item.loaned_amount + amount_borrowed, db=db
        )
        # We add each item to the loan
        loan_content = models_loan.LoanContent(
            loan_id=db_loan.id, item_id=item.id, amount=amount_borrowed
        )
        await cruds_loans.create_loan_content(loan_content=loan_content, db=db)

    res = await cruds_loans.get_loan_by_id(loan_id=db_loan.id, db=db)
    return res


@router.patch(
    "/loans/{loan_id}",
    status_code=204,
    tags=[Tags.loans],
)
async def update_loan(  # noqa: C901
    loan_id: str,
    loan_update: schemas_loans.LoanUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Update a loan and its items.

    As the endpoint can update the loan items, it will send back
    the new representation of the loan `Loan` including the new items relationships

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loan: models_loan.Loan | None = await cruds_loans.get_loan_by_id(
        loan_id=loan_id, db=db
    )
    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loan_id",
        )

    # The user should be a member of the loaner's manager group
    if not is_user_member_of_an_allowed_group(user, [loan.loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loan.loaner_id} loaner",
        )

    # If a new borrower id was provided, it should be a valid user
    if loan_update.borrower_id:
        if not await is_user_id_valid(user_id=loan_update.borrower_id, db=db):
            raise HTTPException(
                status_code=400,
                detail="Invalid user_id",
            )

    # If a new list of items was provided, we need to mark old items as available and new items as not available
    if loan_update.items_borrowed:
        for old_item in loan.items:
            # We need to update the item loaned amount thanks to the amount in the loan content
            loan_content = await cruds_loans.get_loan_content_by_loan_id_item_id(
                loan_id=loan.id,
                item_id=old_item.id,
                db=db,
            )
            if loan_content is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid loan content {loan.id}, {old_item.id}",
                )
            await cruds_loans.update_loaner_item_loaned_amount(
                item_id=old_item.id,
                loaned_amount=old_item.loaned_amount - loan_content.amount,
                db=db,
            )
        # We remove the old items from the database
        await cruds_loans.delete_loan_content_by_loan_id(loan_id=loan_id, db=db)

        items: list[tuple[models_loan.Item, int]] = []

        # All items should be valid, available and belong to the loaner
        for item_borrowed in loan_update.items_borrowed:
            item_id: str = item_borrowed.item_id
            amount_borrowed: int = item_borrowed.amount_borrowed
            item: models_loan.Item | None = await cruds_loans.get_loaner_item_by_id(
                loaner_item_id=item_id, db=db
            )
            if item is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid item_id {item_id}",
                )
            # We check the item belong to the loaner
            if item.loaner_id != loan.loaner_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item {item_id} does not belong to {loan.loaner_id} loaner",
                )
            # We need to check if the amount is available
            available_amount: int = item.total_amount - item.loaned_amount
            isLoanedAmountPossible = amount_borrowed <= available_amount
            if not isLoanedAmountPossible:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item {item_id} is not available",
                )
            # We make a list of every new item with the amount borrowed to update the loaned amount and create the loaned content
            item.loaned_amount += amount_borrowed
            items.append((item, amount_borrowed))

    try:
        # We need to remove the item_ids list from the schema before calling the update_loan crud function
        loan_in_db_update = schemas_loans.LoanInDBUpdate(**loan_update.dict())
        await cruds_loans.update_loan(
            loan_id=loan_id, loan_update=loan_in_db_update, db=db
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    for item, amount_borrowed in items:
        # We update in db the loaned amount for each item
        await cruds_loans.update_loaner_item_loaned_amount(
            item_id=item.id, loaned_amount=item.loaned_amount + amount_borrowed, db=db
        )
        # We add each item to the loan
        loan_content = models_loan.LoanContent(
            loan_id=loan_id, item_id=item.id, amount=amount_borrowed
        )
        await cruds_loans.create_loan_content(loan_content=loan_content, db=db)


@router.delete(
    "/loans/{loan_id}",
    status_code=204,
    tags=[Tags.loans],
)
async def delete_loan(
    loan_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a loan
    This will remove the loan but won't delete any loaner items.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """
    # We need to make sure the user is allowed to manage the loaner
    loan: models_loan.Loan | None = await cruds_loans.get_loan_by_id(
        loan_id=loan_id, db=db
    )
    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loan_id",
        )

    # The user should be a member of the loaner's manager group
    if not is_user_member_of_an_allowed_group(user, [loan.loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loan.loaner_id} loaner",
        )

    # We need to update the item loaned amount thanks to the amount in the loan content
    for item in loan.items:
        loan_content = await cruds_loans.get_loan_content_by_loan_id_item_id(
            loan_id=loan.id,
            item_id=item.id,
            db=db,
        )
        if loan_content is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid loan content {loan.id}, {item.id}",
            )
        await cruds_loans.update_loaner_item_loaned_amount(
            item_id=item.id,
            loaned_amount=item.loaned_amount - loan_content.amount,
            db=db,
        )

    await cruds_loans.delete_loan_content_by_loan_id(loan_id=loan_id, db=db)
    await cruds_loans.delete_loan_by_id(loan_id=loan_id, db=db)


@router.post(
    "/loans/{loan_id}/return",
    status_code=204,
    tags=[Tags.loans],
)
async def return_loan(
    loan_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Mark a loan as returned. This will update items availability.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loan: models_loan.Loan | None = await cruds_loans.get_loan_by_id(
        loan_id=loan_id, db=db
    )
    if loan is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid loan_id",
        )

    # The user should be a member of the loaner's manager group
    if not is_user_member_of_an_allowed_group(user, [loan.loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loan.loaner_id} loaner",
        )

    # We need to update the item loaned amount thanks to the amount in the loan content
    for item in loan.items:
        loan_content = await cruds_loans.get_loan_content_by_loan_id_item_id(
            loan_id=loan.id,
            item_id=item.id,
            db=db,
        )
        if loan_content is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid loan content {loan.id}, {item.id}",
            )
        await cruds_loans.update_loaner_item_loaned_amount(
            item_id=item.id,
            loaned_amount=item.loaned_amount - loan_content.amount,
            db=db,
        )

    await cruds_loans.update_loan_returned_status(
        loan_id=loan_id,
        returned=True,
        db=db,
    )


@router.post(
    "/loans/{loan_id}/extend",
    status_code=204,
    tags=[Tags.loans],
)
async def extend_loan(
    loan_id: str,
    loan_extend: schemas_loans.LoanExtend,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    A new `end` date or an extended `duration` can be provided. If the two are provided, only `end` will be used.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loan: models_loan.Loan | None = await cruds_loans.get_loan_by_id(
        loan_id=loan_id, db=db
    )
    if loan is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid loan_id",
        )

    # The user should be a member of the loaner's manager group
    if not is_user_member_of_an_allowed_group(user, [loan.loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loan.loaner_id} loaner",
        )

    if loan_extend.end is not None:
        loan_update = schemas_loans.LoanUpdate(
            end=loan_extend.end,
        )
    elif loan_extend.duration is not None:
        loan_update = schemas_loans.LoanUpdate(
            end=loan.end + loan_extend.duration,
        )

    await cruds_loans.update_loan(
        loan_id=loan_id,
        loan_update=loan_update,
        db=db,
    )
