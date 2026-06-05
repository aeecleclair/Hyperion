import base64
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.checkout import schemas_checkout
from app.core.checkout.checkout_tool import CheckoutTool
from app.core.checkout.types_checkout import HelloAssoConfigName
from app.core.checkout.utils_checkout import CHECKOUT_EXPIRATION
from app.core.mypayment import cruds_mypayment, models_mypayment, schemas_mypayment
from app.core.mypayment.exceptions_mypayment import (
    InvalidCheckoutToolError,
    InvalidRefundOnTransferError,
    InvalidRequestTypeError,
    InvalidWalletTypeError,
    LinkedWalletNotFoundError,
    PaymentUserNotFoundError,
    TransferAlreadyConfirmedInCallbackError,
    TransferNotFoundByCallbackError,
    TransferTotalDontMatchInCallbackError,
    UnlinkedValidatedRequestError,
    WalletNotFoundOnUpdateError,
)
from app.core.mypayment.integrity_mypayment import (
    format_refund_log,
    format_transaction_log,
    format_transfer_log,
    format_user_fusion_log,
)
from app.core.mypayment.models_mypayment import UserPayment
from app.core.mypayment.schemas_mypayment import SecuredContentData
from app.core.mypayment.types_mypayment import (
    LATEST_TOS,
    MYPAYMENT_LOGS_S3_SUBFOLDER,
    MYPAYMENT_ROOT,
    REQUEST_EXPIRATION,
    RETENTION_DURATION,
    RequestStatus,
    RequestType,
    TransferOrigin,
    WalletType,
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
    data: SecuredContentData,
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
            data.model_dump_json(
                include=set(SecuredContentData.model_fields.keys()),
            ).encode("utf-8"),
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
                call_type=RequestType.TRANSFER_REQUEST,
                module_root=transfer.module,
                object_id=transfer.object_id,
                call_id=transfer.id,
                db=db,
            )


async def request_transaction(
    user: schemas_users.CoreUser,
    request_info: schemas_mypayment.RequestInfo,
    db: AsyncSession,
    notification_tool: NotificationTool,
) -> schemas_mypayment.PaymentRequestInfo:
    """
    Create a Transaction request for a user from a store.
    Create a mypayment payment request between the user wallet and the store wallet
    The request need to be accepted or refused by the user using either
    - /mypayment/requests/{request_id}/accept
    - /mypayment/requests/{request_id}/refuse
    """
    payment_user = await cruds_mypayment.get_user_payment(user.id, db)
    if not payment_user:
        raise PaymentUserNotFoundError(user.id)
    start_time = datetime.now(UTC)
    expiration_time = start_time + timedelta(minutes=REQUEST_EXPIRATION)
    await cruds_mypayment.create_request(
        db=db,
        request=schemas_mypayment.Request(
            id=uuid4(),
            wallet_id=payment_user.wallet_id,
            creation=start_time,
            expiration_date=expiration_time,
            total=request_info.total,
            store_id=request_info.store_id,
            name=request_info.request_name,
            store_note=request_info.store_note,
            module=request_info.module,
            object_id=request_info.object_id,
            status=RequestStatus.PROPOSED,
        ),
    )
    message = Message(
        title=f"💸 Nouvelle demande de paiement - {request_info.request_name}",
        content=f"Une nouvelle demande de paiement de {request_info.total / 100} € attend votre validation",
        action_module=MYPAYMENT_ROOT,
    )
    await notification_tool.send_notification_to_user(
        user_id=user.id,
        message=message,
    )
    return schemas_mypayment.PaymentRequestInfo(
        end_date=expiration_time,
        checkout_url=None,
    )


async def request_transfer(
    user: schemas_users.CoreUser,
    transfer_info: schemas_mypayment.StoreTransferInfo,
    db: AsyncSession,
    payment_tool: CheckoutTool,
    settings: Settings,
) -> schemas_mypayment.PaymentRequestInfo:
    """
    Create a Transfer request for a user from a store.
    The user should be redirected to the returned `checkout_url` to complete the transfer request.
    The transfer will be credited directly to the store wallet.
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
        transfer=schemas_mypayment.TransferCreation(
            id=uuid4(),
            origin=TransferOrigin.HELLO_ASSO,
            approver_user_id=user.id,
            total=transfer_info.amount,
            transfer_identifier=str(checkout.id),
            wallet_id=store.wallet_id,
            creation=datetime.now(UTC),
            confirmed=False,
            module=transfer_info.module,
            object_id=transfer_info.object_id,
        ),
    )

    return schemas_mypayment.PaymentRequestInfo(
        end_date=datetime.now(UTC) + timedelta(minutes=CHECKOUT_EXPIRATION),
        checkout_url=checkout.payment_url,
    )


async def request_payment(
    request_type: RequestType,
    payment_info: schemas_mypayment.PaymentInfo,
    user: schemas_users.CoreUser,
    db: AsyncSession,
    checkout_tool: CheckoutTool,
    notification_tool: NotificationTool,
    settings: Settings,
) -> schemas_mypayment.PaymentRequestInfo:
    """
    Initiate a payment request. This request can be either:
     - a REQUEST_TRANSFER: a checkout will be instantiated, and be credited directly to the store wallet.
        In this case, a `checkout_url` url will be returned, the user should be redirected to this url to complete the checkout.
     - a REQUEST_TRANSACTION: when accepted by the user, a transaction will be created between the user wallet and the store wallet.
        The user should be redirected to mypayment module, to be asked to accept or refuse the transaction request.

    The request is valid until `end_date`

    The `CheckoutTool` must be a *MyPayment* checkout tool

    Use `get_mypayment_tool` dependency to get an instance of `MyPaymentTool`, which will ensure that all dependencies are properly injected.

    When the request is confirmed (checkout validated or transaction accepted), a callback will be called, with the following signature:
    ```python
    async def mypayment_callback(object_id: UUID, db: AsyncSession)
    ```
    """
    # As transfers will be credited to a MyPayment store wallet, we need to ensure that the checkout tool used for transfer requests is a MyPayment checkout tool
    if checkout_tool.name != HelloAssoConfigName.MYPAYMENT:
        raise InvalidCheckoutToolError(checkout_tool.name)

    if request_type == RequestType.TRANSACTION_REQUEST:
        return await request_transaction(
            user=user,
            request_info=schemas_mypayment.RequestInfo(
                total=payment_info.total,
                store_id=payment_info.store_id,
                request_name=payment_info.request_name,
                store_note=payment_info.store_note,
                module=payment_info.module,
                object_id=payment_info.object_id,
            ),
            db=db,
            notification_tool=notification_tool,
        )
    if request_type == RequestType.TRANSFER_REQUEST:
        return await request_transfer(
            user=user,
            transfer_info=schemas_mypayment.StoreTransferInfo(
                amount=payment_info.total,
                store_id=payment_info.store_id,
                module=payment_info.module,
                object_id=payment_info.object_id,
                redirect_url=payment_info.redirect_url,
            ),
            db=db,
            payment_tool=checkout_tool,
            settings=settings,
        )
    raise InvalidRequestTypeError(request_type)


async def apply_transaction(
    user_id: str,
    transaction: schemas_mypayment.TransactionBase,
    debited_wallet_device: models_mypayment.WalletDevice,
    store: models_mypayment.Store,
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
        action_module=MYPAYMENT_ROOT,
    )
    await notification_tool.send_notification_to_user(
        user_id=user_id,
        message=message,
    )


async def refund_request(
    user_id: str,
    request: schemas_mypayment.Request,
    amount: int,
    db: AsyncSession,
    notification_tool: NotificationTool,
):
    """
    Refund a payment request.

    Use `get_mypayment_tool` dependency to get an instance of `MyPaymentTool`, which will ensure that all dependencies are properly injected.
    """
    if request.status != RequestStatus.ACCEPTED:
        raise HTTPException(
            status_code=400,
            detail="Only accepted payment requests can be refunded",
        )
    if amount > request.total:
        raise HTTPException(
            status_code=400,
            detail="Refund amount cannot be greater than the original payment amount",
        )
    if request.transaction_id is None:
        hyperion_error_logger.error(
            f"MyPayment refund: validated request with id {request.id} does not have a transaction_id.",
        )
        raise UnlinkedValidatedRequestError(request.id)
    transaction = await cruds_mypayment.get_transaction(request.transaction_id, db)
    if transaction is None:
        hyperion_error_logger.error(
            f"MyPayment refund: transaction with id {request.transaction_id} not found for request {request.id}.",
        )
        raise UnlinkedValidatedRequestError(request.id)
    wallet = await cruds_mypayment.get_wallet(request.wallet_id, db)
    if wallet is None:
        hyperion_error_logger.error(
            f"MyPayment refund: wallet with id {transaction.debited_wallet_id} not found for transaction {transaction.id}.",
        )
        raise LinkedWalletNotFoundError(transaction.debited_wallet_id)
    if not wallet.user:
        hyperion_error_logger.error(
            f"MyPayment refund: user not found for wallet with id {wallet.id} for transaction {transaction.id}.",
        )
        raise InvalidWalletTypeError(wallet.id, WalletType.USER)
    refund = schemas_mypayment.RefundBase(
        id=uuid4(),
        transaction_id=request.transaction_id,
        total=amount,
        creation=datetime.now(UTC),
        debited_wallet_id=transaction.credited_wallet_id,
        credited_wallet_id=transaction.debited_wallet_id,
    )
    await cruds_mypayment.create_refund(
        db=db,
        refund=refund,
    )
    await cruds_mypayment.increment_wallet_balance(
        wallet_id=transaction.credited_wallet_id,
        amount=-amount,
        db=db,
    )
    await cruds_mypayment.increment_wallet_balance(
        wallet_id=transaction.debited_wallet_id,
        amount=amount,
        db=db,
    )
    hyperion_mypayment_logger.info(
        format_refund_log(refund),
        extra={
            "s3_subfolder": MYPAYMENT_LOGS_S3_SUBFOLDER,
            "s3_retention": RETENTION_DURATION,
        },
    )
    message = Message(
        title=f"💸 Remboursement - {request.name}",
        content=f"Un remboursement de {amount / 100} € a été effectué pour la demande de paiement {request.name}",
        action_module=MYPAYMENT_ROOT,
    )
    await notification_tool.send_notification_to_user(
        user_id=wallet.user.id,
        message=message,
    )


async def refund_direct_transfer(
    transfer: schemas_mypayment.Transfer,
    amount: int,
    db: AsyncSession,
    notification_tool: NotificationTool,
):
    """
    Refund a direct transfer.

    Use `get_mypayment_tool` dependency to get an instance of `MyPaymentTool`, which will ensure that all dependencies are properly injected.
    """
    if not transfer.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Only confirmed transfers can be refunded",
        )
    if not transfer.approver_user_id:
        hyperion_error_logger.error(
            f"MyPayment refund: transfer with id {transfer.id} does not have an approver_user_id.",
        )
        raise InvalidRefundOnTransferError(transfer.id)
    if amount > transfer.total:
        raise HTTPException(
            status_code=400,
            detail="Refund amount cannot be greater than the original transfer amount",
        )
    user_payment = await cruds_mypayment.get_user_payment(transfer.approver_user_id, db)
    if not user_payment:
        hyperion_error_logger.error(
            f"MyPayment refund: user payment not found for approver_user_id {transfer.approver_user_id} for transfer {transfer.id}.",
        )
        raise PaymentUserNotFoundError(transfer.approver_user_id)
    user_wallet = await cruds_mypayment.get_wallet(user_payment.wallet_id, db)
    if user_wallet is None:
        hyperion_error_logger.error(
            f"MyPayment refund: wallet with id {user_payment.wallet_id} not found for transfer {transfer.id}.",
        )
        raise LinkedWalletNotFoundError(user_payment.wallet_id)
    store_wallet = await cruds_mypayment.get_wallet(transfer.wallet_id, db)
    if store_wallet is None or not store_wallet.store:
        hyperion_error_logger.error(
            f"MyPayment refund: store wallet with id {transfer.wallet_id} not found for transfer {transfer.id}.",
        )
        raise LinkedWalletNotFoundError(transfer.wallet_id)
    await cruds_mypayment.increment_wallet_balance(
        wallet_id=transfer.wallet_id,
        amount=-amount,
        db=db,
    )
    await cruds_mypayment.increment_wallet_balance(
        wallet_id=user_wallet.id,
        amount=amount,
        db=db,
    )
    transaction = schemas_mypayment.TransactionBase(
        id=uuid4(),
        debited_wallet_id=transfer.wallet_id,
        credited_wallet_id=user_wallet.id,
        total=amount,
        creation=datetime.now(UTC),
        status=schemas_mypayment.TransactionStatus.CONFIRMED,
        transaction_type=schemas_mypayment.TransactionType.DIRECT,
        seller_user_id=None,
    )
    await cruds_mypayment.create_transaction(
        transaction=transaction,
        debited_wallet_device_id=None,
        store_note=f"Refund for direct transfer {transfer.id}",
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
        title="💸 Remboursement - Transfert direct",
        content=f"Un remboursement de {amount / 100} € a été effectué par {store_wallet.store.name}",
        action_module=MYPAYMENT_ROOT,
    )
    await notification_tool.send_notification_to_user(
        user_id=transfer.approver_user_id,
        message=message,
    )


async def call_mypayment_callback(
    call_type: RequestType,
    module_root: str,
    object_id: UUID,
    call_id: UUID,
    db: AsyncSession,
):
    id_name = (
        "transfer_id" if call_type == RequestType.TRANSFER_REQUEST else "request_id"
    )
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


async def can_user_manage_events(
    user_id: str,
    store_id: UUID,
    db: AsyncSession,
):
    seller = await cruds_mypayment.get_seller(
        user_id=user_id,
        store_id=store_id,
        db=db,
    )
    return seller is not None and seller.can_manage_events
