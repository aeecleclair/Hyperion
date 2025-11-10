import base64
import logging
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memberships import schemas_memberships
from app.core.mypayment import cruds_mypayment, models_mypayment, schemas_mypayment
from app.core.mypayment.integrity_mypayment import format_transfer_log
from app.core.mypayment.models_mypayment import UserPayment
from app.core.mypayment.schemas_mypayment import (
    TransactionRequestInfo,
)
from app.core.mypayment.types_mypayment import (
    TransferAlreadyConfirmedInCallbackError,
    TransferNotFoundByCallbackError,
    TransferTotalDontMatchInCallbackError,
)
from app.core.payment import schemas_payment
from app.core.users import schemas_users

hyperion_security_logger = logging.getLogger("hyperion.security")
hyperion_mypayment_logger = logging.getLogger("hyperion.mypayment")
hyperion_error_logger = logging.getLogger("hyperion.error")

LATEST_TOS = 2
QRCODE_EXPIRATION = 5  # minutes
MYPAYMENT_LOGS_S3_SUBFOLDER = "logs"
RETENTION_DURATION = 10 * 365  # 10 years in days


def verify_signature(
    public_key_bytes: bytes,
    signature: str,
    data: TransactionRequestInfo,
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


async def validate_transfer_callback(
    checkout_payment: schemas_payment.CheckoutPayment,
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


def structure_model_to_schema(
    structure: models_mypayment.Structure,
) -> schemas_mypayment.Structure:
    """
    Convert a structure model to a schema.
    """
    return schemas_mypayment.Structure(
        id=structure.id,
        short_id=structure.short_id,
        name=structure.name,
        association_membership_id=structure.association_membership_id,
        association_membership=schemas_memberships.MembershipSimple(
            id=structure.association_membership.id,
            name=structure.association_membership.name,
            manager_group_id=structure.association_membership.manager_group_id,
        )
        if structure.association_membership
        else None,
        manager_user_id=structure.manager_user_id,
        manager_user=schemas_users.CoreUserSimple(
            id=structure.manager_user.id,
            firstname=structure.manager_user.firstname,
            name=structure.manager_user.name,
            nickname=structure.manager_user.nickname,
            account_type=structure.manager_user.account_type,
            school_id=structure.manager_user.school_id,
        ),
        siret=structure.siret,
        siege_address_street=structure.siege_address_street,
        siege_address_city=structure.siege_address_city,
        siege_address_zipcode=structure.siege_address_zipcode,
        siege_address_country=structure.siege_address_country,
        iban=structure.iban,
        bic=structure.bic,
        creation=structure.creation,
    )


def refund_model_to_schema(
    refund: models_mypayment.Refund,
) -> schemas_mypayment.Refund:
    """
    Convert a refund model to a schema.
    """
    return schemas_mypayment.Refund(
        id=refund.id,
        transaction_id=refund.transaction_id,
        credited_wallet_id=refund.credited_wallet_id,
        debited_wallet_id=refund.debited_wallet_id,
        total=refund.total,
        creation=refund.creation,
        seller_user_id=refund.seller_user_id,
        transaction=schemas_mypayment.Transaction(
            id=refund.transaction.id,
            debited_wallet_id=refund.transaction.debited_wallet_id,
            credited_wallet_id=refund.transaction.credited_wallet_id,
            transaction_type=refund.transaction.transaction_type,
            seller_user_id=refund.transaction.seller_user_id,
            total=refund.transaction.total,
            creation=refund.transaction.creation,
            status=refund.transaction.status,
        ),
        debited_wallet=schemas_mypayment.WalletInfo(
            id=refund.debited_wallet.id,
            type=refund.debited_wallet.type,
            owner_name=refund.debited_wallet.store.name
            if refund.debited_wallet.store
            else refund.debited_wallet.user.full_name
            if refund.debited_wallet.user
            else None,
        ),
        credited_wallet=schemas_mypayment.WalletInfo(
            id=refund.credited_wallet.id,
            type=refund.credited_wallet.type,
            owner_name=refund.credited_wallet.store.name
            if refund.credited_wallet.store
            else refund.credited_wallet.user.full_name
            if refund.credited_wallet.user
            else None,
        ),
    )


def invoice_model_to_schema(
    invoice: models_mypayment.Invoice,
) -> schemas_mypayment.Invoice:
    """
    Convert an invoice model to a schema.
    """
    return schemas_mypayment.Invoice(
        id=invoice.id,
        reference=invoice.reference,
        structure_id=invoice.structure_id,
        creation=invoice.creation,
        start_date=invoice.start_date,
        end_date=invoice.end_date,
        total=invoice.total,
        paid=invoice.paid,
        received=invoice.received,
        structure=structure_model_to_schema(invoice.structure),
        details=[
            schemas_mypayment.InvoiceDetail(
                invoice_id=invoice.id,
                store_id=detail.store_id,
                total=detail.total,
                store=schemas_mypayment.StoreSimple(
                    id=detail.store.id,
                    name=detail.store.name,
                    structure_id=detail.store.structure_id,
                    wallet_id=detail.store.wallet_id,
                    creation=detail.store.creation,
                ),
            )
            for detail in invoice.details
        ],
    )
