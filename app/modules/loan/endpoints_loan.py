import logging
import uuid
from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.notification.schemas_notification import Message
from app.core.users import models_users
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_scheduler,
    is_user_a_member,
    is_user_in,
)
from app.modules.loan import cruds_loan, factory_loan, models_loan, schemas_loan
from app.types.module import Module
from app.types.scheduler import Scheduler
from app.utils.communication.notifications import NotificationTool
from app.utils.tools import (
    is_group_id_valid,
    is_user_id_valid,
    is_user_member_of_any_group,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


module = Module(
    root="loan",
    tag="Loans",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=factory_loan.factory,
)


hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/loans/loaners/",
    response_model=list[schemas_loan.Loaner],
    status_code=200,
)
async def read_loaners(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Get existing loaners.

    **This endpoint is only usable by administrators**
    """

    return await cruds_loan.get_loaners(db=db)


@module.router.post(
    "/loans/loaners/",
    response_model=schemas_loan.Loaner,
    status_code=201,
)
async def create_loaner(
    loaner: schemas_loan.LoanerBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
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

        return await cruds_loan.create_loaner(loaner=loaner_db, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.delete(
    "/loans/loaners/{loaner_id}",
    status_code=204,
)
async def delete_loaner(
    loaner_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a loaner. All items and loans associated with the loaner will also be deleted from the database.

    **This endpoint is only usable by administrators**
    """
    loaner: models_loan.Loaner | None = await cruds_loan.get_loaner_by_id(
        loaner_id=loaner_id,
        db=db,
    )
    if loaner is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loaner_id",
        )

    # We delete all loans associated with this loaner
    for loan in loaner.loans:
        # We first remove LoanContents associated with the loan
        await cruds_loan.delete_loan_content_by_loan_id(loan_id=loan.id, db=db)
        # Then we remove the loan
        await cruds_loan.delete_loan_by_id(loan_id=loan.id, db=db)

    await cruds_loan.delete_loaner_items_by_loaner_id(loaner_id=loaner_id, db=db)
    await cruds_loan.delete_loaner_by_id(loaner_id=loaner_id, db=db)


@module.router.patch(
    "/loans/loaners/{loaner_id}",
    status_code=204,
)
async def update_loaner(
    loaner_id: str,
    loaner_update: schemas_loan.LoanerUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Update a loaner, the request should contain a JSON with the fields to change (not necessarily all fields) and their new value.

    **This endpoint is only usable by administrators**
    """

    await cruds_loan.update_loaner(
        loaner_id=loaner_id,
        loaner_update=loaner_update,
        db=db,
    )


@module.router.get(
    "/loans/loaners/{loaner_id}/loans",
    response_model=list[schemas_loan.Loan],
    status_code=200,
)
async def get_loans_by_loaner(
    loaner_id: str,
    returned: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Return all loans from a given group.


    The query string `returned` can be used to get only return or non returned loans. By default, all loans are returned.


    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loan.get_loaner_by_id(
        loaner_id=loaner_id,
        db=db,
    )
    if loaner is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loaner_id",
        )

    # The user should be a member of the loaner's manager group
    if not is_user_member_of_any_group(user, [loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loaner_id} loaner",
        )

    loans: list[schemas_loan.Loan] = []
    for loan in loaner.loans:
        if returned is None or loan.returned == returned:
            itemsret = await cruds_loan.get_loan_contents_by_loan_id(
                loan_id=loan.id,
                db=db,
            )
            if itemsret is None:
                raise HTTPException(
                    status_code=404,
                    detail="Loan Contents not found",
                )
            items_qty_ret: list[schemas_loan.ItemQuantity] = [
                schemas_loan.ItemQuantity(
                    itemSimple=schemas_loan.ItemSimple(**itemret.item.__dict__),
                    quantity=itemret.quantity,
                )
                for itemret in itemsret
            ]

            loans.append(schemas_loan.Loan(items_qty=items_qty_ret, **loan.__dict__))

    return loans


@module.router.get(
    "/loans/loaners/{loaner_id}/items",
    response_model=list[schemas_loan.Item],
    status_code=200,
)
async def get_items_by_loaner(
    loaner_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Return all items of a loaner.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loan.get_loaner_by_id(
        loaner_id=loaner_id,
        db=db,
    )
    if loaner is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loaner_id",
        )
    # The user should be a member of the loaner's manager group
    if not is_user_member_of_any_group(user, [loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loaner_id} loaner",
        )
    itemret: list[schemas_loan.Item] = []
    for itemDB in loaner.items:
        loaned_quantity = await cruds_loan.get_loaned_quantity(item_id=itemDB.id, db=db)
        itemret.append(
            schemas_loan.Item(loaned_quantity=loaned_quantity, **itemDB.__dict__),
        )

    # We use the ORM relationship capabilities to load items in the loaner object
    return itemret


@module.router.post(
    "/loans/loaners/{loaner_id}/items",
    response_model=schemas_loan.Item,
    status_code=201,
)
async def create_items_for_loaner(
    loaner_id: str,
    item: schemas_loan.ItemBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Create a new item for a loaner. A given loaner can not have more than one item with the same `name`.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loan.get_loaner_by_id(
        loaner_id=loaner_id,
        db=db,
    )
    if loaner is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loaner_id",
        )
    # The user should be a member of the loaner's manager group
    if not is_user_member_of_any_group(user, [loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loaner_id} loaner",
        )

    # We need to check that the loaner does not have another item with the same name
    if (
        await cruds_loan.get_loaner_item_by_name_and_loaner_id(
            loaner_item_name=item.name,
            loaner_id=loaner_id,
            db=db,
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
            total_quantity=item.total_quantity,
            suggested_lending_duration=item.suggested_lending_duration,
        )
        retItem = await cruds_loan.create_item(item=loaner_item_db, db=db)
        return schemas_loan.Item(loaned_quantity=0, **retItem.__dict__)

    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.patch(
    "/loans/loaners/{loaner_id}/items/{item_id}",
    status_code=204,
)
async def update_items_for_loaner(
    loaner_id: str,
    item_id: str,
    item_update: schemas_loan.ItemUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Update a loaner's item.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loan.get_loaner_by_id(
        loaner_id=loaner_id,
        db=db,
    )
    item: models_loan.Item | None = await cruds_loan.get_loaner_item_by_id(
        loaner_item_id=item_id,
        db=db,
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
    if not is_user_member_of_any_group(user, [loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loaner_id} loaner",
        )

    await cruds_loan.update_loaner_item(item_id=item_id, item_update=item_update, db=db)


@module.router.delete(
    "/loans/loaners/{loaner_id}/items/{item_id}",
    status_code=204,
)
async def delete_loaner_item(
    loaner_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a loaner's item.
    This will remove the item from all loans but won't delete any loan.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """
    # We need to make sure the user is allowed to manage the loaner
    item: models_loan.Item | None = await cruds_loan.get_loaner_item_by_id(
        loaner_item_id=item_id,
        db=db,
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
    if not is_user_member_of_any_group(user, [item.loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loaner_id} loaner",
        )

    await cruds_loan.delete_loan_content_by_item_id(item_id=item_id, db=db)
    await cruds_loan.delete_loaner_item_by_id(item_id=item_id, db=db)


@module.router.get(
    "/loans/users/me",
    response_model=list[schemas_loan.Loan],
    status_code=200,
)
async def get_current_user_loans(
    returned: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Return all loans from the current user.

    The query string `returned` can be used to get only returned or non returned loans. By default, all loans are returned.

    **The user must be authenticated to use this endpoint**
    """

    loans_borrowed = await cruds_loan.get_loans_by_borrower(
        db=db,
        borrower_id=user.id,
        returned=returned,
    )

    loansret: list[schemas_loan.Loan] = []
    for loan in loans_borrowed:
        itemsret = await cruds_loan.get_loan_contents_by_loan_id(loan_id=loan.id, db=db)
        if itemsret is None:
            raise HTTPException(
                status_code=404,
                detail="Loan contents not found",
            )
        items_qty_ret: list[schemas_loan.ItemQuantity] = [
            schemas_loan.ItemQuantity(
                itemSimple=schemas_loan.ItemSimple(**itemret.item.__dict__),
                quantity=itemret.quantity,
            )
            for itemret in itemsret
        ]

        loansret.append(schemas_loan.Loan(items_qty=items_qty_ret, **loan.__dict__))

    return loansret


@module.router.get(
    "/loans/users/me/loaners",
    response_model=list[schemas_loan.Loaner],
    status_code=200,
)
async def get_current_user_loaners(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Return all loaners the current user can manage.

    **The user must be authenticated to use this endpoint**
    """

    existing_loaners: Sequence[models_loan.Loaner] = await cruds_loan.get_loaners(db=db)

    user_loaners: list[models_loan.Loaner] = [
        loaner
        for loaner in existing_loaners
        if is_user_member_of_any_group(
            allowed_groups=[loaner.group_manager_id],
            user=user,
        )
    ]

    return user_loaners


@module.router.post(
    "/loans/",
    response_model=schemas_loan.Loan,
    status_code=201,
)
async def create_loan(
    loan_creation: schemas_loan.LoanCreation,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    scheduler: Scheduler = Depends(get_scheduler),
):
    """
    Create a new loan in database and add the requested items

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loaner: models_loan.Loaner | None = await cruds_loan.get_loaner_by_id(
        loaner_id=loan_creation.loaner_id,
        db=db,
    )
    if loaner is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid loaner_id",
        )
    # The user should be a member of the loaner's manager group
    if not is_user_member_of_any_group(user, [loaner.group_manager_id]):
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

    # list of item and quantity borrowed
    items: list[tuple[models_loan.Item, int]] = []

    # All items should be valid, available and belong to the loaner
    for item_borrowed in loan_creation.items_borrowed:
        item_id: str = item_borrowed.item_id
        quantity: int = item_borrowed.quantity

        item: models_loan.Item | None = await cruds_loan.get_loaner_item_by_id(
            loaner_item_id=item_id,
            db=db,
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

        # We need to check if the quantity is available
        loaned_quantity = await cruds_loan.get_loaned_quantity(item_id=item.id, db=db)
        if loaned_quantity is None:
            raise HTTPException(
                status_code=404,
                detail=f"Could not find Item {item_id} loaned_quantity",
            )
        available_quantity: int = item.total_quantity - loaned_quantity
        isLoanedquantityPossible = quantity <= available_quantity
        if not isLoanedquantityPossible:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item_id} is not available",
            )
        # We make a list of every new item with the quantity borrowed to update the loaned quantity and create the loaned content
        items.append((item, quantity))

    db_loan = models_loan.Loan(
        id=str(uuid.uuid4()),
        borrower_id=loan_creation.borrower_id,
        loaner_id=loan_creation.loaner_id,
        start=loan_creation.start,
        end=loan_creation.end,
        notes=loan_creation.notes,
        caution=loan_creation.caution,
        returned=False,  # A newly created loan is still not returned
        items=[],
    )

    try:
        await cruds_loan.create_loan(loan=db_loan, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    for item, quantity in items:
        # We add each item to the loan
        loan_content = models_loan.LoanContent(
            loan_id=db_loan.id,
            item_id=item.id,
            quantity=quantity,
        )
        await cruds_loan.create_loan_content(loan_content=loan_content, db=db)

    loan = await cruds_loan.get_loan_by_id(loan_id=db_loan.id, db=db)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    itemsret = await cruds_loan.get_loan_contents_by_loan_id(loan_id=db_loan.id, db=db)
    if itemsret is None:
        raise HTTPException(status_code=404, detail="LoanContent not found")
    items_qty_ret: list[schemas_loan.ItemQuantity] = [
        schemas_loan.ItemQuantity(
            itemSimple=schemas_loan.ItemSimple(**itemret.item.__dict__),
            quantity=itemret.quantity,
        )
        for itemret in itemsret
    ]

    message = Message(
        title="📦 Nouveau prêt",
        content=f"Un prêt a été enregistré pour l'association {loan.loaner.name}",
        action_module="loan",
    )
    await notification_tool.send_notification_to_user(
        user_id=loan.borrower_id,
        message=message,
    )

    delivery_time = time(11, 00, 00, tzinfo=UTC)
    delivery_datetime = datetime.combine(loan.end, delivery_time, tzinfo=UTC)

    message = Message(
        title="📦 Prêt arrivé à échéance",
        content=f"N'oublie pas de rendre ton prêt à l'association {loan.loaner.name} !",
        action_module="loan",
    )

    await notification_tool.send_notification_to_users(
        user_ids=[loan.borrower_id],
        message=message,
        scheduler=scheduler,
        defer_date=delivery_datetime,
        job_id=f"loan_start_{loan.id}",
    )

    return schemas_loan.Loan(items_qty=items_qty_ret, **loan.__dict__)


@module.router.patch(
    "/loans/{loan_id}",
    status_code=204,
)
async def update_loan(
    loan_id: str,
    loan_update: schemas_loan.LoanUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Update a loan and its items.

    As the endpoint can update the loan items, it will send back
    the new representation of the loan `Loan` including the new items relationships

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loan: models_loan.Loan | None = await cruds_loan.get_loan_by_id(
        loan_id=loan_id,
        db=db,
    )
    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loan_id",
        )

    # The user should be a member of the loaner's manager group
    if not is_user_member_of_any_group(user, [loan.loaner.group_manager_id]):
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
            # We need to update the item loaned quantity thanks to the quantity in the loan content
            loan_content = await cruds_loan.get_loan_content_by_loan_id_item_id(
                loan_id=loan.id,
                item_id=old_item.id,
                db=db,
            )
            if loan_content is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid loan content {loan.id}, {old_item.id}",
                )
        # We remove the old items from the database
        await cruds_loan.delete_loan_content_by_loan_id(loan_id=loan_id, db=db)

        items: list[tuple[models_loan.Item, int]] = []

        # All items should be valid, available and belong to the loaner
        for item_borrowed in loan_update.items_borrowed:
            item_id: str = item_borrowed.item_id
            quantity: int = item_borrowed.quantity
            item: models_loan.Item | None = await cruds_loan.get_loaner_item_by_id(
                loaner_item_id=item_id,
                db=db,
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
            # We need to check if the quantity is available
            loaned_quantity = await cruds_loan.get_loaned_quantity(
                item_id=item.id,
                db=db,
            )
            if loaned_quantity is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Could not find Item {item_id} loaned_quantity",
                )
            available_quantity: int = item.total_quantity - loaned_quantity
            isLoanedquantityPossible = quantity <= available_quantity
            if not isLoanedquantityPossible:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item {item_id} is not available",
                )
            # We make a list of every new item with the quantity borrowed to update the loaned quantity and create the loaned content
            items.append((item, quantity))

    try:
        # We need to remove the item_ids list from the schema before calling the update_loan crud function
        loan_in_db_update = schemas_loan.LoanInDBUpdate(**loan_update.model_dump())
        await cruds_loan.update_loan(
            loan_id=loan_id,
            loan_update=loan_in_db_update,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    for item, quantity in items:
        # We add each item to the loan
        loan_content = models_loan.LoanContent(
            loan_id=loan_id,
            item_id=item.id,
            quantity=quantity,
        )
        await cruds_loan.create_loan_content(loan_content=loan_content, db=db)


@module.router.delete(
    "/loans/{loan_id}",
    status_code=204,
)
async def delete_loan(
    loan_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a loan
    This will remove the loan but won't delete any loaner items.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """
    # We need to make sure the user is allowed to manage the loaner
    loan: models_loan.Loan | None = await cruds_loan.get_loan_by_id(
        loan_id=loan_id,
        db=db,
    )
    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid loan_id",
        )

    # The user should be a member of the loaner's manager group
    if not is_user_member_of_any_group(user, [loan.loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loan.loaner_id} loaner",
        )

    # We need to update the item loaned quantity thanks to the quantity in the loan content
    for item in loan.items:
        loan_content = await cruds_loan.get_loan_content_by_loan_id_item_id(
            loan_id=loan.id,
            item_id=item.id,
            db=db,
        )
        if loan_content is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid loan content {loan.id}, {item.id}",
            )

    await cruds_loan.delete_loan_content_by_loan_id(loan_id=loan_id, db=db)
    await cruds_loan.delete_loan_by_id(loan_id=loan_id, db=db)


@module.router.post(
    "/loans/{loan_id}/return",
    status_code=204,
)
async def return_loan(
    loan_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
    scheduler: Scheduler = Depends(get_scheduler),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Mark a loan as returned. This will update items availability.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loan: models_loan.Loan | None = await cruds_loan.get_loan_by_id(
        loan_id=loan_id,
        db=db,
    )
    if loan is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid loan_id",
        )

    # The user should be a member of the loaner's manager group
    if not is_user_member_of_any_group(user, [loan.loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loan.loaner_id} loaner",
        )

    # We need to update the item loaned quantity thanks to the quantity in the loan content
    for item in loan.items:
        loan_content = await cruds_loan.get_loan_content_by_loan_id_item_id(
            loan_id=loan.id,
            item_id=item.id,
            db=db,
        )
        if loan_content is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid loan content {loan.id}, {item.id}",
            )

    await cruds_loan.update_loan_returned_status(
        loan_id=loan_id,
        db=db,
        returned=True,
        returned_date=datetime.now(UTC),
    )
    await notification_tool.cancel_notification(
        scheduler=scheduler,
        job_id=f"loan_end_{loan.id}",
    )


@module.router.post(
    "/loans/{loan_id}/extend",
    status_code=204,
)
async def extend_loan(
    loan_id: str,
    loan_extend: schemas_loan.LoanExtend,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    scheduler: Scheduler = Depends(get_scheduler),
):
    """
    A new `end` date or an extended `duration` can be provided. If the two are provided, only `end` will be used.

    **The user must be a member of the loaner group_manager to use this endpoint**
    """

    # We need to make sure the user is allowed to manage the loaner
    loan: models_loan.Loan | None = await cruds_loan.get_loan_by_id(
        loan_id=loan_id,
        db=db,
    )
    if loan is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid loan_id",
        )
    end = loan.end
    # The user should be a member of the loaner's manager group
    if not is_user_member_of_any_group(user, [loan.loaner.group_manager_id]):
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized to manage {loan.loaner_id} loaner",
        )

    if loan_extend.end is not None:
        end = loan_extend.end
        loan_update = schemas_loan.LoanUpdate(
            end=end,
        )
    elif loan_extend.duration is not None:
        end = loan.end + timedelta(seconds=loan_extend.duration)
        loan_update = schemas_loan.LoanUpdate(
            end=end,
        )

    await cruds_loan.update_loan(
        loan_id=loan_id,
        loan_update=loan_update,
        db=db,
    )
    await notification_tool.cancel_notification(
        scheduler=scheduler,
        job_id=f"loan_end_{loan.id}",
    )

    message = Message(
        title="📦 Prêt prolongé",
        content=f"Ton prêt à l'association {loan.loaner.name} à bien été renouvellé !",
        action_module="loan",
    )
    await notification_tool.send_notification_to_user(
        user_id=loan.borrower_id,
        message=message,
    )

    delivery_time = time(11, 00, 00, tzinfo=UTC)
    delivery_datetime = datetime.combine(end, delivery_time, tzinfo=UTC)

    message = Message(
        title="📦 Prêt arrivé à échéance",
        content=f"N'oublie pas de rendre ton prêt à l'association {loan.loaner.name} !",
        action_module="loan",
    )

    await notification_tool.send_notification_to_users(
        user_ids=[loan.borrower_id],
        message=message,
        scheduler=scheduler,
        defer_date=delivery_datetime,
        job_id=f"loan_end_{loan.id}",
    )
