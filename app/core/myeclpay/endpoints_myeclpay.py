import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models_core import CoreUser
from app.core.myeclpay import cruds_myeclpay, schemas_myeclpay
from app.core.myeclpay.types_myeclpay import HistoryType, TransactionStatus, WalletType
from app.dependencies import get_db, is_user_an_ecl_member
from app.utils.tools import get_display_name

router = APIRouter(tags=["MyECLPay"])

LATEST_CGU = 1


@router.post(
    "/myeclpay/users/me/register",
    status_code=204,
)
async def register_user(
    signature: schemas_myeclpay.CGUSignature,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Sign MyECL Pay CGU for the given user.

    If the user is already registred in the MyECLPay system, this will update the CGU version.
    If the use has never signed CGU, we will create a new UserPayment and and associated wallet.

    **The user must be authenticated to use this endpoint**
    """
    # Check if user is already registered
    existing_user_payment = await cruds_myeclpay.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if existing_user_payment is None:
        # Create new wallet for user
        wallet_id = uuid.uuid4()
        await cruds_myeclpay.create_wallet(
            wallet_id=wallet_id,
            type=WalletType.USER,
            balance=0,
            db=db,
        )

        # Create new payment user with wallet
        await cruds_myeclpay.create_user_payment(
            user_id=user.id,
            wallet_id=wallet_id,
            accepted_cgu_signature=datetime.now(UTC),
            accepted_cgu_version=signature.accepted_cgu_version,
            db=db,
        )
    else:
        if existing_user_payment.accepted_cgu_version >= signature.accepted_cgu_version:
            raise HTTPException(
                status_code=400,
                detail="You have already signed a more recent CGU version",
            )
        # Update existing user payment
        await cruds_myeclpay.update_user_payment(
            user_id=user.id,
            accepted_cgu_signature=datetime.now(UTC),
            accepted_cgu_version=signature.accepted_cgu_version,
            db=db,
        )

    await db.commit()

    # TODO: maybe send notification and/or mail


@router.get(
    "/myeclpay/users/me/wallet/transactions",
    response_model=list[schemas_myeclpay.History],
)
async def get_user_wallet_transactions(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Get all transactions for the current user's wallet.

    **The user must be authenticated to use this endpoint**
    """
    user_payment = await cruds_myeclpay.get_user_payment(
        user_id=user.id,
        db=db,
    )

    if user_payment is None:
        raise HTTPException(
            status_code=404,
            detail="User is not registered for MyECL Pay",
        )

    history: list[schemas_myeclpay.History] = []

    # First we get all received and send transactions
    transactions = await cruds_myeclpay.get_transactions_by_wallet_id(
        wallet_id=user_payment.wallet_id,
        db=db,
    )

    for transaction in transactions:
        if transaction.receiver_wallet_id == user_payment.wallet_id:
            # The user received the transaction
            transaction_type = HistoryType.RECEIVED
            other_wallet = transaction.giver_wallet
        else:
            # The user sent the transaction
            transaction_type = HistoryType.GIVEN
            other_wallet = transaction.receiver_wallet

        # We need to find if the other wallet correspond to a store or a user to get its display name
        if other_wallet.store is not None:
            other_wallet_name = other_wallet.store.name
        elif other_wallet.user is not None:
            other_wallet_name = get_display_name(
                firstname=other_wallet.user.firstname,
                name=other_wallet.user.name,
                nickname=other_wallet.user.nickname,
            )
        else:
            other_wallet_name = "Unknown"

        history.append(
            schemas_myeclpay.History(
                id=transaction.id,
                type=transaction_type,
                other_wallet_name=other_wallet_name,
                total=transaction.total,
                creation=transaction.creation,
                status=transaction.status,
            ),
        )

    # We also want to include transfers
    transfers = await cruds_myeclpay.get_transfers_by_wallet_id(
        wallet_id=user_payment.wallet_id,
        db=db,
    )

    history.extend(
        schemas_myeclpay.History(
            id=transfer.id,
            type=HistoryType.TRANSFER,
            other_wallet_name="Transfer",
            total=transfer.total,
            creation=transfer.creation,
            status=TransactionStatus.CONFIRMED,
        )
        for transfer in transfers
    )

    return history
    # TODO: limite by datetime
