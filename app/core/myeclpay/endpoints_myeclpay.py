import logging
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models_core import CoreUser
from app.core.myeclpay import cruds_myeclpay, schemas_myeclpay
from app.core.myeclpay.types_myeclpay import (
    HistoryType,
    TransactionStatus,
    TransactionType,
    WalletType,
)
from app.core.myeclpay.utils_myeclpay import compute_signable_data, verify_signature
from app.dependencies import get_db, get_request_id, is_user_an_ecl_member
from app.utils.tools import get_display_name

router = APIRouter(tags=["MyECLPay"])

LATEST_CGU = 1
MAX_TRANSACTION_TOTAL = 2000
QRCODE_EXPIRATION = 5  # minutes

hyperion_error_logger = logging.getLogger("hyperion.error")


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
            wallet_type=WalletType.USER,
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
    "/myeclpay/users/me/wallet/history",
    response_model=list[schemas_myeclpay.History],
)
async def get_user_wallet_history(
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


@router.post(
    "/myeclpay/store/{store_id}/scan",
    response_model=list[schemas_myeclpay.History],
)
async def store_scan_qrcode(
    store_id: UUID,
    qr_code_content: schemas_myeclpay.QRCodeContent,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
    request_id: str = Depends(get_request_id),
):
    """
    Scan and bank a QR code for this store.

    **The user must be authenticated to use this endpoint**
    **The user must have the `can_bank` permission for this store**
    """
    # If the QR Code is already used, we return an error
    already_existing_used_qrcode = await cruds_myeclpay.get_used_qrcode(
        qr_code_id=qr_code_content.qr_code_id,
        db=db,
    )
    if already_existing_used_qrcode is not None:
        raise HTTPException(
            status_code=400,
            detail="QR Code already used",
        )

    # After scanning a QR Code, we want to add it to the list of already scanned QR Code
    # even if it fail to be banked
    await cruds_myeclpay.create_used_qrcode(
        qr_code_id=qr_code_content.qr_code_id,
        db=db,
    )
    await db.commit()

    store = await cruds_myeclpay.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller = await cruds_myeclpay.get_seller_by_user_id_and_store_id(
        store_id=store_id,
        user_id=user.id,
        db=db,
    )

    if seller is None or not seller.can_bank:
        raise HTTPException(
            status_code=400,
            detail="User does not have `can_bank` permission for this store",
        )

    # We verify the signature
    debited_wallet_device = await cruds_myeclpay.get_wallet_device(
        wallet_device_id=qr_code_content.walled_device_id,
        db=db,
    )

    if debited_wallet_device is None:
        raise HTTPException(
            status_code=400,
            detail="Wallet device does not exist",
        )

    if not verify_signature(
        public_key_bytes=debited_wallet_device.ed25519_public_key,
        signature=qr_code_content.signature,
        data=compute_signable_data(qr_code_content),
        wallet_device_id=qr_code_content.walled_device_id,
        request_id=request_id,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid signature",
        )

    # We verify the content respect some rules
    if qr_code_content.total <= 0:
        raise HTTPException(
            status_code=400,
            detail="Total must be greater than 0",
        )

    if qr_code_content.total > MAX_TRANSACTION_TOTAL:
        raise HTTPException(
            status_code=400,
            detail=f"Total can not exceed {MAX_TRANSACTION_TOTAL}",
        )

    if qr_code_content.creation < datetime.now(UTC) - timedelta(
        minutes=QRCODE_EXPIRATION,
    ):
        raise HTTPException(
            status_code=400,
            detail="QR Code is expired",
        )

    # We verify that the debited walled contains enough money
    debited_wallet = await cruds_myeclpay.get_wallet(
        wallet_id=debited_wallet_device.wallet_id,
        db=db,
    )
    if debited_wallet is None:
        hyperion_error_logger.error(
            f"MyECLPay: Could not find wallet associated with the debited wallet device {debited_wallet_device.id}, this should never happen",
        )
        raise HTTPException(
            status_code=400,
            detail="Could not find wallet associated with the debited wallet device",
        )
    if debited_wallet.balance < qr_code_content.total:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance in the debited wallet",
        )

    # We increment the receiving wallet balance
    await cruds_myeclpay.increment_wallet_balance(
        wallet_id=store.wallet_id,
        amount=qr_code_content.total,
        db=db,
    )

    # We decrement the debited wallet balance
    await cruds_myeclpay.increment_wallet_balance(
        wallet_id=debited_wallet.id,
        amount=-qr_code_content.total,
        db=db,
    )

    # We create a transaction
    await cruds_myeclpay.create_transaction(
        transaction_id=uuid.uuid4(),
        giver_wallet_id=debited_wallet_device.id,
        giver_wallet_device_id=debited_wallet_device.id,
        receiver_wallet_id=store.wallet_id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=user.id,
        total=qr_code_content.total,
        creation=datetime.now(UTC),
        status=TransactionStatus.CONFIRMED,
        store_note=None,
        db=db,
    )

    # TODO: log the transaction
