import base64
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.checkout import schemas_checkout
from app.core.checkout.payment_tool import PaymentTool
from app.core.memberships import schemas_memberships
from app.core.mypayment import cruds_mypayment, models_mypayment, schemas_mypayment
from app.core.mypayment.exceptions_mypayment import (
    TransferAlreadyConfirmedInCallbackError,
    TransferNotFoundByCallbackError,
    TransferTotalDontMatchInCallbackError,
    WalletNotFoundOnUpdateError,
)
from app.core.mypayment.integrity_mypayment import (
    format_transaction_log,
    format_transfer_log,
    format_user_fusion_log,
)
from app.core.mypayment.models_mypayment import UserPayment
from app.core.mypayment.schemas_mypayment import (
    QRCodeContentData,
    RequestValidationData,
)
from app.core.mypayment.types_mypayment import (
    LATEST_TOS,
    MYPAYMENT_LOGS_S3_SUBFOLDER,
    MYPAYMENT_ROOT,
    RETENTION_DURATION,
    MyPaymentCallType,
    RequestStatus,
    TransferType,
)
from app.core.notification.schemas_notification import Message
from app.core.users import schemas_users
from app.core.utils.config import Settings
from app.module import all_modules
from app.utils.communication.notifications import NotificationTool

hyperion_security_logger = logging.getLogger("hyperion.security")
hyperion_mypayment_logger = logging.getLogger("hyperion.mypayment")
hyperion_error_logger = logging.getLogger("hyperion.error")


def verify_signature(
    public_key_bytes: bytes,
    signature: str,
    data: QRCodeContentData | RequestValidationData,
    wallet_device_id: UUID,
    request_id: str,
) -> bool:
    """
    Verify the signature of `data` with `signature` using ed25519.
    """
    try:
        loaded_public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        loaded_public_key.verify(
            base64.decodebytes(signature.encode("utf-8")),
            data.model_dump_json(exclude={"signature", "bypass_membership"}).encode(
                "utf-8",
            ),
        )
    except InvalidSignature:
        hyperion_security_logger.info(
            f"MyPayment: Invalid signature for QR Code with WalletDevice {wallet_device_id} ({request_id})",
        )
        return False
    except Exception as error:
        hyperion_security_logger.info(
            f"MyPayment: Failed to verify signature for QR Code with WalletDevice {wallet_device_id}: {error} ({request_id})",
        )
        return False
    return True


def is_user_latest_tos_signed(
    user_payment: UserPayment,
) -> bool:
    """
    Check if the user has signed the latest TOS version.
    """

    return user_payment.accepted_tos_version == LATEST_TOS


async def fuse_mypayment_users_utils(
    db: AsyncSession,
    user_kept_id: str,
    user_deleted_id: str,
):
    """
    Fuse two users in MyPayment by updating all rows with user_deleted_id to user_kept_id.
    """
    await cruds_mypayment.fuse_mypayment_users(
        db=db,
        user_kept_id=user_kept_id,
        user_deleted_id=user_deleted_id,
    )
    hyperion_mypayment_logger.info(
        format_user_fusion_log(
            user_kept_id=user_kept_id,
            user_deleted_id=user_deleted_id,
        ),
        extra={
            "s3_subfolder": MYPAYMENT_LOGS_S3_SUBFOLDER,
            "s3_retention": RETENTION_DURATION,
        },
    )


async def validate_transfer_callback(
    checkout_payment: schemas_checkout.CheckoutPayment,
    db: AsyncSession,
):
    paid_amount = checkout_payment.paid_amount
    checkout_id = checkout_payment.checkout_id

    transfer = await cruds_mypayment.get_transfer_by_transfer_identifier(
        db=db,
        transfer_identifier=str(checkout_id),
    )
    if not transfer:
        hyperion_error_logger.error(
            f"MyPayment payment callback: user transfer with transfer identifier {checkout_id} not found.",
        )
        raise TransferNotFoundByCallbackError(checkout_id)

    wallet = await cruds_mypayment.get_wallet(transfer.wallet_id, db)

    if not wallet:
        hyperion_error_logger.error(
            f"MyPayment payment callback: wallet with id {transfer.wallet_id} not found for transfer {transfer.id}.",
        )
        raise WalletNotFoundOnUpdateError(transfer.wallet_id)

    if transfer.total != paid_amount:
        hyperion_error_logger.error(
            f"MyPayment payment callback: user transfer {transfer.id} amount does not match the paid amount.",
        )
        raise TransferTotalDontMatchInCallbackError(checkout_id)

    if transfer.confirmed:
        hyperion_error_logger.error(
            f"MyPayment payment callback: user transfer {transfer.id} is already confirmed.",
        )
        raise TransferAlreadyConfirmedInCallbackError(checkout_id)

    await cruds_mypayment.confirm_transfer(
        db=db,
        transfer_id=transfer.id,
    )
    await cruds_mypayment.increment_wallet_balance(
        db=db,
        wallet_id=transfer.wallet_id,
        amount=paid_amount,
    )

    hyperion_mypayment_logger.info(
        format_transfer_log(transfer),
        extra={
            "s3_subfolder": MYPAYMENT_LOGS_S3_SUBFOLDER,
            "s3_retention": RETENTION_DURATION,
        },
    )
    if wallet.store:  # This transfer is a direct transfer to a store, it was requested by a module, so we want to call the module callback if it exists
        if transfer.module and transfer.object_id:
            await call_mypayment_callback(
                call_type=MyPaymentCallType.TRANSFER,
                module_root=transfer.module,
                object_id=transfer.object_id,
                call_id=transfer.id,
                db=db,
            )


async def request_transaction(
    user_id: str,
    store_id: UUID,
    total: int,
    name: str,
    note: str | None,
    module: str,
    object_id: UUID,
    db: AsyncSession,
    notification_tool: NotificationTool,
    settings: Settings,
) -> UUID:
    """
    Create a transaction request for a user from a store.
    """
    payment_user = await cruds_mypayment.get_user_payment(user_id, db)
    if not payment_user:
        raise HTTPException(
            status_code=400,
            detail=f"User {user_id} does not have a payment account",
        )
    request_id = uuid4()
    await cruds_mypayment.create_request(
        db=db,
        request=schemas_mypayment.Request(
            id=request_id,
            wallet_id=payment_user.wallet_id,
            creation=datetime.now(UTC),
            total=total,
            store_id=store_id,
            name=name,
            store_note=note,
            module=module,
            object_id=object_id,
            status=RequestStatus.PROPOSED,
        ),
    )
    message = Message(
        title=f"💸 Nouvelle demande de paiement - {name}",
        content=f"Une nouvelle demande de paiement de {total / 100} € attend votre validation",
        action_module=settings.school.payment_name,
    )
    await notification_tool.send_notification_to_user(
        user_id=user_id,
        message=message,
    )
    return request_id


async def request_store_transfer(
    user: schemas_users.CoreUser,
    transfer_info: schemas_mypayment.StoreTransferInfo,
    db: AsyncSession,
    payment_tool: PaymentTool,
    settings: Settings,
) -> schemas_checkout.PaymentUrl:
    """
    Create a direct transfer to a store
    """
    if transfer_info.redirect_url not in settings.TRUSTED_PAYMENT_REDIRECT_URLS:
        hyperion_error_logger.warning(
            f"User {user.id} tried to redirect to an untrusted URL: {transfer_info.redirect_url}",
        )
        raise HTTPException(
            status_code=400,
            detail="Redirect URL is not trusted by hyperion",
        )

    if transfer_info.amount < 100:
        raise HTTPException(
            status_code=400,
            detail="Please give an amount in cents, greater than 1€.",
        )

    store = await cruds_mypayment.get_store(transfer_info.store_id, db)
    if not store:
        raise HTTPException(
            status_code=404,
            detail=f"Store with id {transfer_info.store_id} not found",
        )

    checkout = await payment_tool.init_checkout(
        module=MYPAYMENT_ROOT,
        checkout_amount=transfer_info.amount,
        checkout_name=f"Recharge {settings.school.payment_name}",
        redirection_uri=f"{settings.CLIENT_URL}mypayment/transfer/redirect?url={transfer_info.redirect_url}",
        payer_user=user,
        db=db,
    )

    await cruds_mypayment.create_transfer(
        db=db,
        transfer=schemas_mypayment.Transfer(
            id=uuid4(),
            type=TransferType.HELLO_ASSO,
            approver_user_id=None,
            total=transfer_info.amount,
            transfer_identifier=str(checkout.id),
            wallet_id=store.wallet_id,
            creation=datetime.now(UTC),
            confirmed=False,
            module=transfer_info.module,
            object_id=transfer_info.object_id,
        ),
    )

    return schemas_checkout.PaymentUrl(
        url=checkout.payment_url,
    )


async def apply_transaction(
    user_id: str,
    transaction: schemas_mypayment.TransactionBase,
    debited_wallet_device: models_mypayment.WalletDevice,
    store: models_mypayment.Store,
    settings: Settings,
    notification_tool: NotificationTool,
    db: AsyncSession,
):
    # We increment the receiving wallet balance
    await cruds_mypayment.increment_wallet_balance(
        wallet_id=transaction.credited_wallet_id,
        amount=transaction.total,
        db=db,
    )

    # We decrement the debited wallet balance
    await cruds_mypayment.increment_wallet_balance(
        wallet_id=transaction.debited_wallet_id,
        amount=-transaction.total,
        db=db,
    )
    # We create a transaction
    await cruds_mypayment.create_transaction(
        transaction=transaction,
        debited_wallet_device_id=debited_wallet_device.id,
        store_note=None,
        db=db,
    )

    hyperion_mypayment_logger.info(
        format_transaction_log(transaction),
        extra={
            "s3_subfolder": MYPAYMENT_LOGS_S3_SUBFOLDER,
            "s3_retention": RETENTION_DURATION,
        },
    )
    message = Message(
        title=f"💳 Paiement - {store.name}",
        content=f"Une transaction de {transaction.total / 100} € a été effectuée",
        action_module=settings.school.payment_name,
    )
    await notification_tool.send_notification_to_user(
        user_id=user_id,
        message=message,
    )


async def call_mypayment_callback(
    call_type: MyPaymentCallType,
    module_root: str,
    object_id: UUID,
    call_id: UUID,
    db: AsyncSession,
):
    id_name = "transfer_id" if call_type == MyPaymentCallType.TRANSFER else "request_id"
    try:
        for module in all_modules:
            if module.root == module_root:
                if module.mypayment_callback is None:
                    hyperion_error_logger.info(
                        f"MyPayment: module {module_root} does not define a request callback ({id_name}: {call_id})",
                    )
                    return
                hyperion_error_logger.info(
                    f"MyPayment: calling module {module_root} request callback",
                )
                await module.mypayment_callback(object_id, db)
                hyperion_error_logger.info(
                    f"MyPayment: call to module {module_root} request callback ({id_name}: {call_id}) succeeded",
                )
                return

        hyperion_error_logger.info(
            f"MyPayment: request callback for module {module_root} not found ({id_name}: {call_id})",
        )
    except Exception:
        hyperion_error_logger.exception(
            f"MyPayment: call to module {module_root} request callback ({id_name}: {call_id}) failed",
        )
