import logging
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric import ed25519

from app.core.myeclpay.models_myeclpay import UserPayment
from app.core.myeclpay.schemas_myeclpay import (
    QRCodeContentBase,
    QRCodeContentData,
)

hyperion_security_logger = logging.getLogger("hyperion.security")


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
