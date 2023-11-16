import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_tricount
from app.dependencies import get_db, is_user_a_member
from app.models import models_core, models_tricount
from app.schemas import schemas_tricount
from app.utils.types.tags import Tags

router = APIRouter()


async def if_user_a_member_of_sharer_group(
    user_id: str, sharer_group_id: str, db: AsyncSession
) -> bool:
    user_membership = (
        await cruds_tricount.get_sharer_group_membership_by_user_id_and_group_id(
            user_id=user_id,
            sharer_group_id=sharer_group_id,
            db=db,
        )
    )
    return user_membership is not None


async def generate_sharer_group_detail(
    sharer_group: models_tricount.SharerGroup,
) -> schemas_tricount.SharerGroup:
    # We need to compute the sharer group detail
    solde_details = {user.id: 0.0 for user in sharer_group.members}
    total: float = 0

    for transaction in sharer_group.transactions:
        solde_details[transaction.payer_id] += transaction.amount
        total += transaction.amount

        per_person_amount = transaction.amount / len(transaction.beneficiaries)

        for beneficiary in transaction.beneficiaries:
            solde_details[beneficiary.id] -= per_person_amount

    balances: list[schemas_tricount.Balance] = []
    for user_id, balance in solde_details.items():
        balances.append(schemas_tricount.Balance(user_id=user_id, amount=balance))

    sharer_group_schema = schemas_tricount.SharerGroup(
        id=sharer_group.id,
        name=sharer_group.name,
        members=sharer_group.members,
        transactions=sharer_group.transactions,
        total=total,
        balances=balances,
    )

    return sharer_group_schema


@router.get(
    "/tricount/sharergroups/memberships",
    response_model=list[schemas_tricount.SharerGroupMembership],
    status_code=200,
    tags=[Tags.tricount],
)
async def get_sharer_group_memberships(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return all sharer groups membership belonging to a user.
    The front wil need to query sharer groups detail one by one as computing
    sharer groups detail take some time.

    **The user need to be authenticated to use this endpoint**
    """

    return await cruds_tricount.get_sharer_group_memberships_by_user_id(
        user_id=user.id, db=db
    )


@router.post(
    "/tricount/sharergroups/memberships",
    status_code=204,
    tags=[Tags.tricount],
)
async def add_sharergroup_membership(
    new_sharer_group_membership: schemas_tricount.SharerGroupMembership,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Update a sharer group

    **The user need to be authenticated and member of the sharer group to use this endpoint**
    """

    if not if_user_a_member_of_sharer_group(
        user_id=user.id,
        sharer_group_id=new_sharer_group_membership.sharer_group_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    # The membership may already exist be be inactive
    membership = (
        await cruds_tricount.get_sharer_group_membership_by_user_id_and_group_id(
            user_id=new_sharer_group_membership.user_id,
            sharer_group_id=new_sharer_group_membership.sharer_group_id,
            db=db,
        )
    )
    if membership is None:
        new_sharer_group_membership_model = models_tricount.SharerGroupMembership(
            **new_sharer_group_membership.dict()
        )
        await cruds_tricount.create_sharer_group_membership(
            sharer_group_membership=new_sharer_group_membership_model,
            db=db,
        )
    elif membership.active:
        raise HTTPException(
            status_code=409,
            detail="This membership already exists",
        )

    # We reactivate the membership
    await cruds_tricount.update_sharer_group_membership_active_status(
        db=db,
        sharer_group_id=new_sharer_group_membership.sharer_group_id,
        user_id=new_sharer_group_membership.user_id,
        active=True,
    )


@router.delete(
    "/tricount/sharergroups/{sharer_group_id}/membership/{membership_id}",
    status_code=204,
    tags=[Tags.tricount],
)
async def delete_sharergroup_membership(
    sharer_group_id: str,
    membership_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Update a sharer group

    **The user need to be authenticated and member of the sharer group to use this endpoint**
    """

    if not if_user_a_member_of_sharer_group(
        user_id=user.id,
        sharer_group_id=sharer_group_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    await cruds_tricount.update_sharer_group_membership_active_status(
        db=db,
        sharer_group_id=sharer_group_id,
        user_id=membership_id,
        active=False,
    )


@router.get(
    "/tricount/sharergroups/{sharer_group_id}",
    response_model=schemas_tricount.SharerGroup,
    status_code=200,
    tags=[Tags.tricount],
)
async def get_sharer_group_by_id(
    sharer_group_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return a sharer group details.

    **The user need to be authenticated a be a member of the sharer group to use this endpoint**
    """

    sharer_group = await cruds_tricount.get_sharer_groups_by_id(
        sharer_group_id=sharer_group_id, db=db
    )

    if sharer_group is None:
        raise HTTPException(
            status_code=404,
            detail="Sharer group not found",
        )

    if not if_user_a_member_of_sharer_group(
        user_id=user.id,
        sharer_group_id=sharer_group_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    return await generate_sharer_group_detail(
        sharer_group=sharer_group,
    )


@router.post(
    "/tricount/sharergroups",
    response_model=schemas_tricount.SharerGroup,
    status_code=201,
    tags=[Tags.tricount],
)
async def create_sharer_groups(
    sharer_group: schemas_tricount.SharerGroupBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a new sharer group

    **The user need to be authenticated to use this endpoint**
    """

    sharer_group_id = str(uuid.uuid4())

    sharer_group_model = models_tricount.SharerGroup(
        id=sharer_group_id, name=sharer_group.name, transactions=[], members=[]
    )

    await cruds_tricount.create_sharer_group(sharer_group=sharer_group_model, db=db)

    # We want to add the user that created the group as a member
    await cruds_tricount.create_sharer_group_membership(
        db=db,
        sharer_group_membership=models_tricount.SharerGroupMembership(
            sharer_group_id=sharer_group_id,
            user_id=user.id,
            position=0,
            active=True,
        ),
    )

    new_sharer_group_model = await cruds_tricount.get_sharer_groups_by_id(
        sharer_group_id=sharer_group_id, db=db
    )
    if new_sharer_group_model is None:
        raise HTTPException(
            status_code=500,
            detail="Could not find created sharer group",
        )
    return await generate_sharer_group_detail(
        sharer_group=new_sharer_group_model,
    )


@router.patch(
    "/tricount/sharergroups/{sharer_group_id}",
    status_code=204,
    tags=[Tags.tricount],
)
async def update_sharer_groups(
    sharer_group_id: str,
    sharer_group_update: schemas_tricount.SharerGroupUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Update a sharer group

    **The user need to be authenticated and member of the sharer group to use this endpoint**
    """

    if not if_user_a_member_of_sharer_group(
        user_id=user.id,
        sharer_group_id=sharer_group_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    return await cruds_tricount.update_sharer_group(
        sharer_group_update=sharer_group_update, sharer_group_id=sharer_group_id, db=db
    )


@router.post(
    "/tricount/transactions",
    response_model=schemas_tricount.Transaction,
    status_code=201,
    tags=[Tags.tricount],
)
async def create_transaction(
    transaction: schemas_tricount.TransactionCreate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Create a new transaction

    **The user need to be authenticated and member of the sharer group to use this endpoint**
    """

    if not if_user_a_member_of_sharer_group(
        user_id=user.id,
        sharer_group_id=transaction.sharer_group_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    transaction_id = str(uuid.uuid4())

    transaction_model = models_tricount.Transaction(
        id=transaction_id,
        sharer_group_id=transaction.sharer_group_id,
        amount=transaction.amount,
        type=transaction.type,
        title=transaction.title,
        description=transaction.description,
        creator_id=user.id,
        payer_id=transaction.payer_id,
    )

    await cruds_tricount.create_transaction(transaction=transaction_model, db=db)

    for user_id in transaction.beneficiaries_user_ids:
        await cruds_tricount.create_transaction_beneficiary(
            db=db,
            transaction_beneficiary=models_tricount.TransactionBeneficiariesMembership(
                transaction_id=transaction_id, user_id=user_id
            ),
        )

    return await cruds_tricount.get_transaction_by_id(
        transaction_id=transaction_id, db=db
    )


@router.patch(
    "/tricount/transactions/{transaction_id}",
    response_model=schemas_tricount.Transaction,
    status_code=200,
    tags=[Tags.tricount],
)
async def update_transaction(
    transaction_id: str,
    transaction_update: schemas_tricount.TransactionUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Update a transaction

    **The user need to be authenticated and member of the sharer group to use this endpoint**
    """

    existing_transaction = await cruds_tricount.get_transaction_by_id(
        transaction_id=transaction_id, db=db
    )
    if existing_transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    if not if_user_a_member_of_sharer_group(
        user_id=user.id,
        sharer_group_id=existing_transaction.sharer_group_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    transaction_update_base = schemas_tricount.TransactionUpdateBase(
        **transaction_update.dict()
    )
    await cruds_tricount.update_transaction(
        transaction_update=transaction_update_base, transaction_id=transaction_id, db=db
    )

    # If we need to change beneficiaries, we delete all beneficiaries and recreate the new ones
    if transaction_update.beneficiaries_user_ids is not None:
        await cruds_tricount.delete_transaction_beneficiaries(
            transaction_id=transaction_id, db=db
        )
        for user_id in transaction_update.beneficiaries_user_ids:
            await cruds_tricount.create_transaction_beneficiary(
                db=db,
                transaction_beneficiary=models_tricount.TransactionBeneficiariesMembership(
                    transaction_id=transaction_id, user_id=user_id
                ),
            )

    return await cruds_tricount.get_transaction_by_id(
        transaction_id=transaction_id, db=db
    )


@router.delete(
    "/tricount/transactions/{transaction_id}",
    status_code=204,
    tags=[Tags.tricount],
)
async def delete_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Delete a transaction

    **The user need to be authenticated and member of the sharer group to use this endpoint**
    """

    existing_transaction = await cruds_tricount.get_transaction_by_id(
        transaction_id=transaction_id, db=db
    )
    if existing_transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    if not if_user_a_member_of_sharer_group(
        user_id=user.id,
        sharer_group_id=existing_transaction.sharer_group_id,
        db=db,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group",
        )

    await cruds_tricount.delete_transaction_beneficiaries(
        transaction_id=transaction_id,
        db=db,
    )

    await cruds_tricount.delete_transaction(transaction_id=transaction_id, db=db)
