import logging
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.myeclpay import cruds_myeclpay
from app.core.myeclpay.models_myeclpay import UserPayment
from app.core.myeclpay.schemas_myeclpay import (
    QRCodeContentBase,
    QRCodeContentData,
)
from app.core.payment import schemas_payment

hyperion_security_logger = logging.getLogger("hyperion.security")

hyperion_error_logger = logging.getLogger("hyperion.error")

LATEST_TOS = 1
TOS_CONTENT = "TOS Content"
MAX_TRANSACTION_TOTAL = 2000
QRCODE_EXPIRATION = 5  # minutes


def compute_signable_data(content: QRCodeContentBase) -> bytes:
    return (
        QRCodeContentData(
            id=content.qr_code_id,
            tot=content.total,
            iat=content.creation,
            key=content.walled_device_id,
            store=content.store,
        )
        .model_dump_json()
        .encode("utf-8")
    )


def verify_signature(
    public_key_bytes: bytes,
    signature: bytes,
    data: bytes,
    wallet_device_id: UUID,
    request_id: str,
) -> bool:
    """
    Verify the signature of `data` with `signature` using ed25519.
    """
    try:
        loaded_public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        loaded_public_key.verify(
            signature,
            data,
        )
    except Exception as error:
        hyperion_security_logger.info(
            f"MyECLPay: Failed to verify signature for QR Code with WalletDevice {wallet_device_id}: {error} ({request_id})",
        )
        return False
    else:
        return True


def is_user_latest_tos_signed(
    user_payment: UserPayment,
) -> bool:
    """
    Check if the user has signed the latest TOS version.
    """

    return user_payment.accepted_tos_version == LATEST_TOS


async def validate_transfer(
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
            f"MyECLPay payment callback: user transfer {checkout_id} not found.",
        )
        raise ValueError(f"User transfer {checkout_id} not found.")  # noqa: TRY003
    try:
        await cruds_myeclpay.confirm_transfer(
            db=db,
            transfer_id=transfer.id,
        )
        await cruds_myeclpay.increment_wallet_balance(
            db=db,
            wallet_id=transfer.wallet_id,
            amount=paid_amount,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
