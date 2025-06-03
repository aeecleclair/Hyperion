import base64
import logging
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.myeclpay import cruds_myeclpay
from app.core.myeclpay.integrity_myeclpay import format_transfer_log
from app.core.myeclpay.models_myeclpay import UserPayment
from app.core.myeclpay.schemas_myeclpay import (
    QRCodeContentData,
)
from app.core.myeclpay.types_myeclpay import (
    TransferAlreadyConfirmedInCallbackError,
    TransferNotFoundByCallbackError,
    TransferTotalDontMatchInCallbackError,
)
from app.core.payment import schemas_payment

hyperion_security_logger = logging.getLogger("hyperion.security")
hyperion_myeclpay_logger = logging.getLogger("hyperion.myeclpay")
hyperion_error_logger = logging.getLogger("hyperion.error")

LATEST_TOS = 2
MAX_TRANSACTION_TOTAL = 2000
QRCODE_EXPIRATION = 5  # minutes


def verify_signature(
    public_key_bytes: bytes,
    signature: str,
    data: QRCodeContentData,
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
            f"MyECLPay: Invalid signature for QR Code with WalletDevice {wallet_device_id} ({request_id})",
        )
        return False
    except Exception as error:
        hyperion_security_logger.info(
            f"MyECLPay: Failed to verify signature for QR Code with WalletDevice {wallet_device_id}: {error} ({request_id})",
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


async def validate_transfer_callback(
    checkout_payment: schemas_payment.CheckoutPayment,
    db: AsyncSession,
):
    paid_amount = checkout_payment.paid_amount
    checkout_id = checkout_payment.checkout_id

    transfer = await cruds_myeclpay.get_transfer_by_transfer_identifier(
        db=db,
        transfer_identifier=str(checkout_id),
    )
    if not transfer:
        hyperion_error_logger.error(
            f"MyECLPay payment callback: user transfer with transfer identifier {checkout_id} not found.",
        )
        raise TransferNotFoundByCallbackError(checkout_id)

    if transfer.total != paid_amount:
        hyperion_error_logger.error(
            f"MyECLPay payment callback: user transfer {transfer.id} amount does not match the paid amount.",
        )
        raise TransferTotalDontMatchInCallbackError(checkout_id)

    if transfer.confirmed:
        hyperion_error_logger.error(
            f"MyECLPay payment callback: user transfer {transfer.id} is already confirmed.",
        )
        raise TransferAlreadyConfirmedInCallbackError(checkout_id)

    await cruds_myeclpay.confirm_transfer(
        db=db,
        transfer_id=transfer.id,
    )
    await cruds_myeclpay.increment_wallet_balance(
        db=db,
        wallet_id=transfer.wallet_id,
        amount=paid_amount,
    )

    hyperion_myeclpay_logger.info(format_transfer_log(transfer))
