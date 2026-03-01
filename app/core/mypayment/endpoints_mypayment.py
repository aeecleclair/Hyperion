import base64
import logging
import re
import urllib.parse
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import calypsso
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
)
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import schemas_auth
from app.core.core_endpoints import cruds_core
from app.core.groups.groups_type import GroupType
from app.core.memberships.utils_memberships import (
    get_user_active_membership_to_association_membership,
)
from app.core.mypayment import cruds_mypayment, schemas_mypayment
from app.core.mypayment.coredata_mypayment import MyPaymentBankAccountHolder
from app.core.mypayment.dependencies_mypayment import is_user_bank_account_holder
from app.core.mypayment.exceptions_mypayment import (
    InvoiceNotFoundAfterCreationError,
    ReferencedStructureNotFoundError,
)
from app.core.mypayment.factory_mypayment import MyPaymentFactory
from app.core.mypayment.integrity_mypayment import (
    format_cancel_log,
    format_refund_log,
    format_transaction_log,
    format_withdrawal_log,
)
from app.core.mypayment.models_mypayment import Store, WalletDevice
from app.core.mypayment.types_mypayment import (
    HistoryType,
    TransactionStatus,
    TransactionType,
    TransferType,
    UnexpectedError,
    WalletDeviceStatus,
    WalletType,
)
from app.core.mypayment.utils.data_exporter import generate_store_history_csv
from app.core.mypayment.utils_mypayment import (
    LATEST_TOS,
    QRCODE_EXPIRATION,
    is_user_latest_tos_signed,
    structure_model_to_schema,
    validate_transfer_callback,
    verify_signature,
)
from app.core.notification.schemas_notification import Message
from app.core.payment import schemas_payment
from app.core.payment.payment_tool import PaymentTool
from app.core.payment.types_payment import HelloAssoConfigName
from app.core.users import cruds_users, schemas_users
from app.core.users.models_users import CoreUser
from app.core.utils import security
from app.core.utils.config import Settings
from app.dependencies import (
    get_db,
    get_mail_templates,
    get_notification_tool,
    get_payment_tool,
    get_request_id,
    get_settings,
    get_token_data,
    is_user,
    is_user_an_ecl_member,
    is_user_in,
)
from app.types import standard_responses
from app.types.module import CoreModule
from app.types.scopes_type import ScopeType
from app.utils.auth.auth_utils import get_user_id_from_token_with_scopes
from app.utils.communication.notifications import NotificationTool
from app.utils.mail.mailworker import send_email
from app.utils.tools import (
    generate_pdf_from_template,
    get_core_data,
    get_file_from_data,
    set_core_data,
)

router = APIRouter(tags=["MyPayment"])

core_module = CoreModule(
    root="mypayment",
    tag="MyPayment",
    router=router,
    payment_callback=validate_transfer_callback,
    factory=MyPaymentFactory(),
)


hyperion_error_logger = logging.getLogger("hyperion.error")
hyperion_security_logger = logging.getLogger("hyperion.security")
hyperion_mypayment_logger = logging.getLogger("hyperion.mypayment")

MYPAYMENT_STRUCTURE_S3_SUBFOLDER = "structures"
MYPAYMENT_STORES_S3_SUBFOLDER = "stores"
MYPAYMENT_USERS_S3_SUBFOLDER = "users"
MYPAYMENT_DEVICES_S3_SUBFOLDER = "devices"
MYPAYMENT_LOGS_S3_SUBFOLDER = "logs"
RETENTION_DURATION = 10 * 365  # 10 years in days


@router.get(
    "/mypayment/bank-account-holder",
    response_model=schemas_mypayment.Structure,
    status_code=200,
)
async def get_bank_account_holder(
    user: CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current bank account holder information.
    """
    bank_account_holder = await get_core_data(
        MyPaymentBankAccountHolder,
        db=db,
    )
    structure = await cruds_mypayment.get_structure_by_id(
        db=db,
        structure_id=bank_account_holder.holder_structure_id,
    )
    if structure is None:
        raise ReferencedStructureNotFoundError(
            structure_id=bank_account_holder.holder_structure_id,
        )
    return structure


@router.post(
    "/mypayment/bank-account-holder",
    response_model=schemas_mypayment.Structure,
    status_code=201,
)
async def set_bank_account_holder(
    bank_account_info: MyPaymentBankAccountHolder,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """Set the bank account holder information."""

    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=bank_account_info.holder_structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )

    await set_core_data(
        bank_account_info,
        db=db,
    )

    return structure


@router.get(
    "/mypayment/structures",
    status_code=200,
    response_model=list[schemas_mypayment.Structure],
)
async def get_structures(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get all structures.
    """
    return await cruds_mypayment.get_structures(
        db=db,
    )


@router.post(
    "/mypayment/structures",
    status_code=201,
    response_model=schemas_mypayment.Structure,
)
async def create_structure(
    structure: schemas_mypayment.StructureBase,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new structure.

    A structure contains:
     - a name
     - an association membership id
     - a manager user id
     - a list of stores

    **The user must be an admin to use this endpoint**
    """
    db_user = await cruds_users.get_user_by_id(
        user_id=structure.manager_user_id,
        db=db,
    )
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="Manager user does not exist",
        )
    structure_db = schemas_mypayment.StructureSimple(
        id=uuid.uuid4(),
        short_id=structure.short_id,
        name=structure.name,
        association_membership_id=structure.association_membership_id,
        manager_user_id=structure.manager_user_id,
        siege_address_street=structure.siege_address_street,
        siege_address_zipcode=structure.siege_address_zipcode,
        siege_address_city=structure.siege_address_city,
        siege_address_country=structure.siege_address_country,
        iban=structure.iban,
        bic=structure.bic,
        creation=datetime.now(tz=UTC),
    )
    await cruds_mypayment.create_structure(
        structure=structure_db,
        db=db,
    )

    hyperion_mypayment_logger.info(
        structure_db.name,
        extra={
            "s3_subfolder": MYPAYMENT_STRUCTURE_S3_SUBFOLDER,
            "s3_filename": str(structure_db.id),
        },
    )

    return await cruds_mypayment.get_structure_by_id(structure_db.id, db)


@router.patch(
    "/mypayment/structures/{structure_id}",
    status_code=204,
)
async def update_structure(
    structure_id: UUID,
    structure_update: schemas_mypayment.StructureUpdate,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Update a structure.

    **The user must be an admin to use this endpoint**
    """
    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )

    await cruds_mypayment.update_structure(
        structure_id=structure_id,
        structure_update=structure_update,
        db=db,
    )

    hyperion_mypayment_logger.info(
        structure.name,
        extra={
            "s3_subfolder": MYPAYMENT_STRUCTURE_S3_SUBFOLDER,
            "s3_filename": str(structure.id),
        },
    )


@router.delete(
    "/mypayment/structures/{structure_id}",
    status_code=204,
)
async def delete_structure(
    structure_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a structure. Only structures without stores can be deleted.

    **The user must be an admin to use this endpoint**
    """
    stores = await cruds_mypayment.get_stores_by_structure_id(
        structure_id=structure_id,
        db=db,
    )
    if stores:
        raise HTTPException(
            status_code=400,
            detail="Structure has stores",
        )

    await cruds_mypayment.delete_structure(
        structure_id=structure_id,
        db=db,
    )


@router.post(
    "/mypayment/structures/{structure_id}/admin/{user_id}",
    status_code=201,
)
async def create_structure_administrator(
    structure_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Create a new administrator for a structure.

    **The user must be a manager to use this endpoint**
    """
    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )
    if structure.manager_user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="User is not the manager for this structure",
        )

    db_user = await cruds_users.get_user_by_id(
        user_id=user_id,
        db=db,
    )
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="User does not exist",
        )
    admin_db = (
        await cruds_mypayment.get_structure_administrator_by_user_id_and_structure_id(
            user_id=user_id,
            structure_id=structure_id,
            db=db,
        )
    )
    if admin_db is not None:
        raise HTTPException(
            status_code=400,
            detail="User is already an admin",
        )

    await cruds_mypayment.create_structure_administrator(
        user_id=user_id,
        structure_id=structure_id,
        db=db,
    )

    # We will add the new manager as a seller for all stores of the structure
    stores = await cruds_mypayment.get_stores_by_structure_id(
        structure_id=structure_id,
        db=db,
    )
    sellers = await cruds_mypayment.get_sellers_by_user_id(
        user_id=user_id,
        db=db,
    )
    sellers_store_ids = [seller.store_id for seller in sellers]
    for store in stores:
        if store.id not in sellers_store_ids:
            await cruds_mypayment.create_seller(
                user_id=user_id,
                store_id=store.id,
                can_bank=True,
                can_see_history=True,
                can_cancel=True,
                can_manage_sellers=True,
                db=db,
            )
        else:
            await cruds_mypayment.update_seller(
                seller_user_id=user_id,
                store_id=store.id,
                seller_update=schemas_mypayment.SellerUpdate(
                    can_bank=True,
                    can_see_history=True,
                    can_cancel=True,
                    can_manage_sellers=True,
                ),
                db=db,
            )
    return db_user


@router.delete(
    "/mypayment/structures/{structure_id}/admin/{user_id}",
    status_code=204,
)
async def delete_structure_administrator(
    structure_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Delete an administrator for a structure.

    **The user must be a manager to use this endpoint**
    """
    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )
    if structure.manager_user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="User is not the manager for this structure",
        )
    admin_db = (
        await cruds_mypayment.get_structure_administrator_by_user_id_and_structure_id(
            user_id=user_id,
            structure_id=structure_id,
            db=db,
        )
    )
    if admin_db is None:
        raise HTTPException(
            status_code=400,
            detail="User is not an admin",
        )

    await cruds_mypayment.delete_structure_administrator(
        user_id=user_id,
        structure_id=structure_id,
        db=db,
    )

    # We will remove critical administrator's rights for all stores of the structure
    stores = await cruds_mypayment.get_stores_by_structure_id(
        structure_id=structure_id,
        db=db,
    )

    for store in stores:
        await cruds_mypayment.update_seller(
            seller_user_id=user_id,
            store_id=store.id,
            seller_update=schemas_mypayment.SellerUpdate(
                can_cancel=False,
                can_manage_sellers=False,
            ),
            db=db,
        )


@router.post(
    "/mypayment/structures/{structure_id}/init-manager-transfer",
    status_code=201,
)
async def init_transfer_structure_manager(
    structure_id: UUID,
    transfer_info: schemas_mypayment.StructureTranfert,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    mail_templates: calypsso.MailTemplates = Depends(get_mail_templates),
    settings: Settings = Depends(get_settings),
):
    """
    Initiate the transfer of a structure to a new manager. The current manager will receive an email with a link to confirm the transfer.
    The link will only be valid for a limited time.

    **The user must be the manager for this structure**
    """
    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )
    if structure.manager_user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="User is not the manager for this structure",
        )

    # If a previous transfer request exists, delete it
    await cruds_mypayment.delete_structure_manager_transfer_by_structure(
        structure_id=structure_id,
        db=db,
    )

    wanted_new_manager = await cruds_users.get_user_by_id(
        user_id=transfer_info.new_manager_user_id,
        db=db,
    )
    if wanted_new_manager is None:
        raise HTTPException(
            status_code=404,
            detail="New manager user does not exist",
        )

    confirmation_token = security.generate_token()

    await cruds_mypayment.init_structure_manager_transfer(
        structure_id=structure_id,
        user_id=transfer_info.new_manager_user_id,
        confirmation_token=confirmation_token,
        valid_until=datetime.now(tz=UTC)
        + timedelta(minutes=settings.MYPAYMENT_MANAGER_TRANSFER_TOKEN_EXPIRES_MINUTES),
        db=db,
    )

    confirmation_url = f"{settings.CLIENT_URL}mypayment/structures/confirm-manager-transfer?token={confirmation_token}"

    if settings.SMTP_ACTIVE:
        mail = mail_templates.get_mail_mypayment_structure_transfer(
            confirmation_url=confirmation_url,
        )

        background_tasks.add_task(
            send_email,
            recipient=user.email,
            subject="MyECL - Confirm the structure manager transfer",
            content=mail,
            settings=settings,
        )
    else:
        hyperion_security_logger.info(
            f"You can confirm the transfer by clicking the following link: {confirmation_url}",
        )


@router.get(
    "/mypayment/structures/confirm-manager-transfer",
    status_code=200,
)
async def confirm_structure_manager_transfer(
    token: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Update a manager for an association

    The user must have initiated the update of the manager with `init_update_structure_manager`
    """

    request = await cruds_mypayment.get_structure_manager_transfer_by_secret(
        confirmation_token=token,
        db=db,
    )
    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Request does not exist",
        )

    if request.valid_until < datetime.now(UTC):
        raise HTTPException(
            status_code=400,
            detail="Request has expired",
        )

    await cruds_mypayment.update_structure_manager(
        structure_id=request.structure_id,
        manager_user_id=request.user_id,
        db=db,
    )

    # We will add the new manager as a seller for all stores of the structure
    stores = await cruds_mypayment.get_stores_by_structure_id(
        structure_id=request.structure_id,
        db=db,
    )
    sellers = await cruds_mypayment.get_sellers_by_user_id(
        user_id=request.user_id,
        db=db,
    )
    sellers_store_ids = [seller.store_id for seller in sellers]
    for store in stores:
        if store.id not in sellers_store_ids:
            await cruds_mypayment.create_seller(
                user_id=request.user_id,
                store_id=store.id,
                can_bank=True,
                can_see_history=True,
                can_cancel=True,
                can_manage_sellers=True,
                db=db,
            )
        else:
            await cruds_mypayment.update_seller(
                seller_user_id=request.user_id,
                store_id=store.id,
                seller_update=schemas_mypayment.SellerUpdate(
                    can_bank=True,
                    can_see_history=True,
                    can_cancel=True,
                    can_manage_sellers=True,
                ),
                db=db,
            )

    return RedirectResponse(
        url=settings.CLIENT_URL
        + calypsso.get_message_relative_url(
            message_type=calypsso.TypeMessage.mypayment_structure_transfer_success,
        ),
    )


@router.post(
    "/mypayment/structures/{structure_id}/stores",
    status_code=201,
    response_model=schemas_mypayment.Store,
)
async def create_store(
    structure_id: UUID,
    store: schemas_mypayment.StoreBase,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Create a store. The structure manager will be added as a seller for the store.

    Stores name should be unique, as an user need to be able to identify a store by its name.

    **The user must be the manager for this structure**
    """
    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )
    if structure.manager_user_id != user.id and user.id not in [
        user.id for user in structure.administrators
    ]:
        raise HTTPException(
            status_code=403,
            detail="User is not the manager for this structure",
        )

    existing_store_with_name = await cruds_mypayment.get_store_by_name(
        name=store.name,
        db=db,
    )
    if existing_store_with_name is not None:
        raise HTTPException(
            status_code=400,
            detail="Store with this name already exists in this structure",
        )

    # Create new wallet for store
    wallet_id = uuid.uuid4()
    await cruds_mypayment.create_wallet(
        wallet_id=wallet_id,
        wallet_type=WalletType.STORE,
        balance=0,
        db=db,
    )
    # Create new store
    store_db = Store(
        id=uuid.uuid4(),
        name=store.name,
        structure_id=structure_id,
        wallet_id=wallet_id,
        creation=datetime.now(tz=UTC),
    )
    await cruds_mypayment.create_store(
        store=store_db,
        db=db,
    )
    await db.flush()

    # Add manager as a full right seller for the store
    await cruds_mypayment.create_seller(
        user_id=structure.manager_user_id,
        store_id=store_db.id,
        can_bank=True,
        can_see_history=True,
        can_cancel=True,
        can_manage_sellers=True,
        db=db,
    )
    for admin in structure.administrators:
        await cruds_mypayment.create_seller(
            user_id=admin.id,
            store_id=store_db.id,
            can_bank=True,
            can_see_history=True,
            can_cancel=True,
            can_manage_sellers=True,
            db=db,
        )

    hyperion_mypayment_logger.info(
        f"store.name: {store_db.name}, structure_id: {store_db.structure_id}",
        extra={
            "s3_subfolder": MYPAYMENT_STORES_S3_SUBFOLDER,
            "s3_filename": str(store_db.id),
        },
    )

    return schemas_mypayment.Store(
        id=store_db.id,
        name=store_db.name,
        structure_id=store_db.structure_id,
        wallet_id=store_db.wallet_id,
        creation=store_db.creation,
        structure=structure,
    )


@router.get(
    "/mypayment/stores/{store_id}/history",
    status_code=200,
    response_model=list[schemas_mypayment.History],
)
async def get_store_history(
    store_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get all transactions for the store.

    **The user must be authorized to see the store history**
    """
    store = await cruds_mypayment.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller = await cruds_mypayment.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller is None or not seller.can_see_history:
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to see the store history",
        )

    history = []

    transactions = await cruds_mypayment.get_transactions_by_wallet_id(
        wallet_id=store.wallet_id,
        db=db,
        start_datetime=start_date,
        end_datetime=end_date,
    )
    for transaction in transactions:
        history_refund: schemas_mypayment.HistoryRefund | None = None
        if transaction.refund is not None:
            history_refund = schemas_mypayment.HistoryRefund(
                total=transaction.refund.total,
                creation=transaction.refund.creation,
            )

        if transaction.debited_wallet_id == store.wallet_id:
            history.append(
                schemas_mypayment.History(
                    id=transaction.id,
                    type=HistoryType.GIVEN,
                    total=transaction.total,
                    status=transaction.status,
                    creation=transaction.creation,
                    other_wallet_name=transaction.credited_wallet.user.full_name
                    if transaction.credited_wallet.user is not None
                    else "",
                    refund=history_refund,
                ),
            )
        else:
            history.append(
                schemas_mypayment.History(
                    id=transaction.id,
                    type=HistoryType.RECEIVED,
                    total=transaction.total,
                    status=transaction.status,
                    creation=transaction.creation,
                    other_wallet_name=transaction.debited_wallet.user.full_name
                    if transaction.debited_wallet.user is not None
                    else "",
                    refund=history_refund,
                ),
            )

    transfers = await cruds_mypayment.get_transfers_by_wallet_id(
        wallet_id=store.wallet_id,
        db=db,
        start_datetime=start_date,
        end_datetime=end_date,
    )
    if len(transfers) > 0:
        hyperion_error_logger.error(
            f"Store {store.id} should never have transfers",
        )

    # We add refunds
    refunds = await cruds_mypayment.get_refunds_by_wallet_id(
        wallet_id=store.wallet_id,
        db=db,
        start_datetime=start_date,
        end_datetime=end_date,
    )
    for refund in refunds:
        if refund.debited_wallet_id == store.wallet_id:
            transaction_type = HistoryType.REFUND_DEBITED
            other_wallet_info = refund.credited_wallet
        else:
            transaction_type = HistoryType.REFUND_CREDITED
            other_wallet_info = refund.debited_wallet

        history.append(
            schemas_mypayment.History(
                id=refund.id,
                type=transaction_type,
                other_wallet_name=other_wallet_info.owner_name or "Unknown",
                total=refund.total,
                creation=refund.creation,
                status=TransactionStatus.CONFIRMED,
            ),
        )

    return history


@router.get(
    "/mypayment/stores/{store_id}/history/data-export",
    status_code=200,
    response_model=None,
)
async def export_store_history(
    store_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Export store payment history as a CSV file.
    """
    store = await cruds_mypayment.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller = await cruds_mypayment.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller is None or not seller.can_see_history:
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to see the store history",
        )

    transactions_with_sellers = (
        await cruds_mypayment.get_transactions_and_sellers_by_wallet_id(
            wallet_id=store.wallet_id,
            db=db,
            start_datetime=start_date,
            end_datetime=end_date,
        )
    )

    transfers_with_sellers = (
        await cruds_mypayment.get_transfers_and_sellers_by_wallet_id(
            wallet_id=store.wallet_id,
            db=db,
            start_datetime=start_date,
            end_datetime=end_date,
        )
    )
    if len(transfers_with_sellers) > 0:
        hyperion_error_logger.error(
            f"Store {store.id} should never have transfers",
        )

    # We add refunds
    refunds_with_sellers = await cruds_mypayment.get_refunds_and_sellers_by_wallet_id(
        wallet_id=store.wallet_id,
        db=db,
        start_datetime=start_date,
        end_datetime=end_date,
    )

    # Create refunds map
    refunds_map = {
        refund.transaction_id: (refund, seller_name)
        for refund, seller_name in refunds_with_sellers
    }

    # Generate CSV content
    csv_content = generate_store_history_csv(
        transactions_with_sellers=list(transactions_with_sellers),
        refunds_map=refunds_map,
        store_wallet_id=store.wallet_id,
    )

    # Generate filename
    date_range = ""
    if start_date and end_date:
        date_range = (
            f"_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}"
        )
    elif start_date:
        date_range = f"_from_{start_date.strftime('%Y-%m-%d')}"
    elif end_date:
        date_range = f"_until_{end_date.strftime('%Y-%m-%d')}"

    # Sanitize store name for filename
    safe_store_name = "".join(
        c for c in store.name if c.isalnum() or c in (" ", "-", "_")
    ).rstrip()

    filename = f"store_history_{safe_store_name}{date_range}.csv"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return Response(
        csv_content,
        headers=headers,
        media_type="text/csv; charset=utf-8",
    )


@router.get(
    "/mypayment/users/me/stores",
    status_code=200,
    response_model=list[schemas_mypayment.UserStore],
)
async def get_user_stores(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get all stores for the current user.

    **The user must be authenticated to use this endpoint**
    """
    sellers = await cruds_mypayment.get_sellers_by_user_id(
        user_id=user.id,
        db=db,
    )

    stores: list[schemas_mypayment.UserStore] = []
    for seller in sellers:
        store = await cruds_mypayment.get_store(
            store_id=seller.store_id,
            db=db,
        )
        if store is not None:
            stores.append(
                schemas_mypayment.UserStore(
                    id=store.id,
                    name=store.name,
                    creation=store.creation,
                    structure_id=store.structure_id,
                    structure=structure_model_to_schema(store.structure),
                    wallet_id=store.wallet_id,
                    can_bank=seller.can_bank,
                    can_see_history=seller.can_see_history,
                    can_cancel=seller.can_cancel,
                    can_manage_sellers=seller.can_manage_sellers,
                ),
            )

    return stores


@router.patch(
    "/mypayment/stores/{store_id}",
    status_code=204,
)
async def update_store(
    store_id: UUID,
    store_update: schemas_mypayment.StoreUpdate,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Update a store

    **The user must be the manager for this store's structure**
    """
    store = await cruds_mypayment.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=store.structure_id,
        db=db,
    )
    if structure is None or (
        structure.manager_user_id != user.id
        and user.id not in [user.id for user in structure.administrators]
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not the manager for this structure",
        )

    await cruds_mypayment.update_store(
        store_id=store_id,
        store_update=store_update,
        db=db,
    )

    hyperion_mypayment_logger.info(
        f"store.name: {store.name}, structure_id: {store.structure_id}",
        extra={
            "s3_subfolder": MYPAYMENT_STORES_S3_SUBFOLDER,
            "s3_filename": str(store.id),
        },
    )


@router.delete(
    "/mypayment/stores/{store_id}",
    status_code=204,
)
async def delete_store(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Delete a store. Only stores without transactions can be deleted.

    **The user must be the manager for this store's structure**
    """
    store = await cruds_mypayment.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=store.structure_id,
        db=db,
    )
    if structure is None or (
        structure.manager_user_id != user.id
        and user.id not in [user.id for user in structure.administrators]
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not the manager for this structure",
        )

    transactions = await cruds_mypayment.get_transactions_by_wallet_id(
        wallet_id=store.wallet_id,
        db=db,
    )
    transfers = await cruds_mypayment.get_transfers_by_wallet_id(
        wallet_id=store.wallet_id,
        db=db,
    )
    refunds = await cruds_mypayment.get_refunds_by_wallet_id(
        wallet_id=store.wallet_id,
        db=db,
    )
    if len(transactions) > 0 or len(transfers) > 0 or len(refunds) > 0:
        raise HTTPException(
            status_code=400,
            detail="Store has items in history and cannot be deleted anymore",
        )

    sellers = await cruds_mypayment.get_sellers_by_store_id(
        store_id=store_id,
        db=db,
    )
    for seller in sellers:
        await cruds_mypayment.delete_seller(
            seller_user_id=seller.user_id,
            store_id=store_id,
            db=db,
        )

    await cruds_mypayment.delete_store(
        store_id=store_id,
        db=db,
    )


@router.post(
    "/mypayment/stores/{store_id}/sellers",
    status_code=201,
    response_model=schemas_mypayment.Seller,
)
async def create_store_seller(
    store_id: UUID,
    seller: schemas_mypayment.SellerCreation,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Create a store seller.

    This seller will have authorized permissions among:
    - can_bank
    - can_see_history
    - can_cancel
    - can_manage_sellers

    **The user must have the `can_manage_sellers` permission for this store**
    """
    store = await cruds_mypayment.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller_admin = await cruds_mypayment.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller_admin is None or not seller_admin.can_manage_sellers:
        raise HTTPException(
            status_code=403,
            detail="User does not have the permission to manage sellers",
        )

    existing_seller = await cruds_mypayment.get_seller(
        user_id=seller.user_id,
        store_id=store_id,
        db=db,
    )
    if existing_seller is not None:
        raise HTTPException(
            status_code=400,
            detail="Seller already exists",
        )

    await cruds_mypayment.create_seller(
        user_id=seller.user_id,
        store_id=store_id,
        can_bank=seller.can_bank,
        can_see_history=seller.can_see_history,
        can_cancel=seller.can_cancel,
        can_manage_sellers=seller.can_manage_sellers,
        db=db,
    )

    return await cruds_mypayment.get_seller(
        user_id=seller.user_id,
        store_id=store_id,
        db=db,
    )


@router.get(
    "/mypayment/stores/{store_id}/sellers",
    status_code=200,
    response_model=list[schemas_mypayment.Seller],
)
async def get_store_sellers(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get all sellers for the given store.

    **The user must have the `can_manage_sellers` permission for this store**
    """
    store = await cruds_mypayment.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller_admin = await cruds_mypayment.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller_admin is None or not seller_admin.can_manage_sellers:
        raise HTTPException(
            status_code=403,
            detail="User does not have the permission to manage sellers",
        )

    return await cruds_mypayment.get_sellers_by_store_id(
        store_id=store_id,
        db=db,
    )


@router.patch(
    "/mypayment/stores/{store_id}/sellers/{seller_user_id}",
    status_code=204,
)
async def update_store_seller(
    store_id: UUID,
    seller_user_id: str,
    seller_update: schemas_mypayment.SellerUpdate,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Update a store seller permissions.
    The structure manager cannot be updated as a seller.

    **The user must have the `can_manage_sellers` permission for this store**
    """

    store = await cruds_mypayment.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller_admin = await cruds_mypayment.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller_admin is None or not seller_admin.can_manage_sellers:
        raise HTTPException(
            status_code=403,
            detail="User does not have the permission to manage sellers",
        )

    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=store.structure_id,
        db=db,
    )
    if (
        structure is None
        or structure.manager_user_id == seller_user_id
        or (
            seller_user_id in [user.id for user in structure.administrators]
            and structure.manager_user_id != user.id
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="User is the manager for this structure and cannot be updated as a seller",
        )

    seller = await cruds_mypayment.get_seller(
        user_id=seller_user_id,
        store_id=store_id,
        db=db,
    )

    if seller is None:
        raise HTTPException(
            status_code=404,
            detail="Seller does not exist",
        )

    await cruds_mypayment.update_seller(
        seller_user_id=seller_user_id,
        store_id=store_id,
        seller_update=seller_update,
        db=db,
    )


@router.delete(
    "/mypayment/stores/{store_id}/sellers/{seller_user_id}",
    status_code=204,
)
async def delete_store_seller(
    store_id: UUID,
    seller_user_id: str,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Delete a store seller.
    The structure manager cannot be deleted as a seller.

    **The user must have the `can_manage_sellers` permission for this store**
    """
    store = await cruds_mypayment.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller_admin = await cruds_mypayment.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller_admin is None or not seller_admin.can_manage_sellers:
        raise HTTPException(
            status_code=403,
            detail="User does not have the permission to manage sellers",
        )

    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=store.structure_id,
        db=db,
    )
    if (
        structure is None
        or structure.manager_user_id == seller_user_id
        or (
            seller_user_id in [user.id for user in structure.administrators]
            and structure.manager_user_id != user.id
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="User is the manager for this structure and cannot be deleted as a seller",
        )

    seller = await cruds_mypayment.get_seller(
        user_id=seller_user_id,
        store_id=store_id,
        db=db,
    )

    if seller is None:
        raise HTTPException(
            status_code=404,
            detail="Seller does not exist",
        )

    await cruds_mypayment.delete_seller(
        seller_user_id=seller_user_id,
        store_id=store_id,
        db=db,
    )


@router.post(
    "/mypayment/users/me/register",
    status_code=204,
)
async def register_user(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Sign MyECL Pay TOS for the given user.

    The user will need to accept the latest TOS version to be able to use MyECL Pay.

    **The user must be authenticated to use this endpoint**
    """

    # Check if user is already registered
    existing_user_payment = await cruds_mypayment.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if existing_user_payment is not None:
        raise HTTPException(
            status_code=400,
            detail="User is already registered for MyECL Pay",
        )

    # Create new wallet for user
    wallet_id = uuid.uuid4()
    await cruds_mypayment.create_wallet(
        wallet_id=wallet_id,
        wallet_type=WalletType.USER,
        balance=0,
        db=db,
    )

    await db.flush()

    # Create new payment user with wallet
    await cruds_mypayment.create_user_payment(
        user_id=user.id,
        wallet_id=wallet_id,
        accepted_tos_signature=datetime.now(UTC),
        accepted_tos_version=0,
        db=db,
    )

    hyperion_mypayment_logger.info(
        wallet_id,
        extra={
            "s3_subfolder": MYPAYMENT_USERS_S3_SUBFOLDER,
            "s3_filename": str(user.id),
        },
    )


@router.get(
    "/mypayment/users/me/tos",
    status_code=200,
    response_model=schemas_mypayment.TOSSignatureResponse,
)
async def get_user_tos(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
):
    """
    Get the latest TOS version and the user signed TOS version.

    **The user must be authenticated to use this endpoint**
    """
    # Check if user is already registered
    existing_user_payment = await cruds_mypayment.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if existing_user_payment is None:
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    return schemas_mypayment.TOSSignatureResponse(
        accepted_tos_version=existing_user_payment.accepted_tos_version,
        latest_tos_version=LATEST_TOS,
        tos_content=Path("assets/mypayment-terms-of-service.txt").read_text("utf-8"),
        max_wallet_balance=settings.MYPAYMENT_MAXIMUM_WALLET_BALANCE,
    )


@router.post(
    "/mypayment/users/me/tos",
    status_code=204,
)
async def sign_tos(
    signature: schemas_mypayment.TOSSignature,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    mail_templates: calypsso.MailTemplates = Depends(get_mail_templates),
    settings: Settings = Depends(get_settings),
):
    """
    Sign MyECL Pay TOS for the given user.

    If the user is already registered in the MyPayment system, this will update the TOS version.

    **The user must be authenticated to use this endpoint**
    """
    if signature.accepted_tos_version != LATEST_TOS:
        raise HTTPException(
            status_code=400,
            detail=f"Only the latest TOS version {LATEST_TOS} can be accepted",
        )

    # Check if user is already registered
    existing_user_payment = await cruds_mypayment.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if existing_user_payment is None:
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    # Update existing user payment
    await cruds_mypayment.update_user_payment(
        user_id=user.id,
        accepted_tos_signature=datetime.now(UTC),
        accepted_tos_version=signature.accepted_tos_version,
        db=db,
    )

    # TODO: add logs
    if settings.SMTP_ACTIVE:
        mail = mail_templates.get_mail_mypayment_tos_signed(
            tos_version=signature.accepted_tos_version,
            tos_url=settings.CLIENT_URL
            + calypsso.get_asset_relative_url(
                asset=calypsso.Asset.mypayment_terms_of_service,
            ),
        )

        background_tasks.add_task(
            send_email,
            recipient=user.email,
            subject="MyECL - You signed the Terms of Service for MyPayment",
            content=mail,
            settings=settings,
        )


@router.get(
    "/mypayment/users/me/wallet/devices",
    status_code=200,
    response_model=list[schemas_mypayment.WalletDevice],
)
async def get_user_devices(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get user devices.

    **The user must be authenticated to use this endpoint**
    """
    # Check if user is already registered
    user_payment = await cruds_mypayment.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if user_payment is None:
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    return await cruds_mypayment.get_wallet_devices_by_wallet_id(
        wallet_id=user_payment.wallet_id,
        db=db,
    )


@router.get(
    "/mypayment/users/me/wallet/devices/{wallet_device_id}",
    status_code=200,
    response_model=schemas_mypayment.WalletDevice,
)
async def get_user_device(
    wallet_device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get user devices.

    **The user must be authenticated to use this endpoint**
    """
    # Check if user is already registered
    user_payment = await cruds_mypayment.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if user_payment is None:
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    wallet_device = await cruds_mypayment.get_wallet_device(
        wallet_device_id=wallet_device_id,
        db=db,
    )

    if wallet_device is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet device does not exist",
        )

    if wallet_device.wallet_id != user_payment.wallet_id:
        raise HTTPException(
            status_code=400,
            detail="Wallet device does not belong to the user",
        )

    return wallet_device


@router.get(
    "/mypayment/users/me/wallet",
    status_code=200,
    response_model=schemas_mypayment.Wallet,
)
async def get_user_wallet(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get user wallet.

    **The user must be authenticated to use this endpoint**
    """
    # Check if user is already registered
    user_payment = await cruds_mypayment.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if user_payment is None:
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    wallet = await cruds_mypayment.get_wallet(
        wallet_id=user_payment.wallet_id,
        db=db,
    )

    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet does not exist",
        )

    return wallet


@router.post(
    "/mypayment/users/me/wallet/devices",
    status_code=201,
    response_model=schemas_mypayment.WalletDevice,
)
async def create_user_devices(
    wallet_device_creation: schemas_mypayment.WalletDeviceCreation,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    mail_templates: calypsso.MailTemplates = Depends(get_mail_templates),
    settings: Settings = Depends(get_settings),
):
    """
    Create a new device for the user.
    The user will need to activate it using a token sent by email.

    **The user must be authenticated to use this endpoint**
    """
    # Check if user is already registered
    user_payment = await cruds_mypayment.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if user_payment is None or not is_user_latest_tos_signed(user_payment):
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    activation_token = security.generate_token(nbytes=16)

    wallet_device_db = WalletDevice(
        id=uuid.uuid4(),
        name=wallet_device_creation.name,
        wallet_id=user_payment.wallet_id,
        ed25519_public_key=base64.decodebytes(
            wallet_device_creation.ed25519_public_key,
        ),
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.INACTIVE,
        activation_token=activation_token,
    )

    await cruds_mypayment.create_wallet_device(
        wallet_device=wallet_device_db,
        db=db,
    )

    if settings.SMTP_ACTIVE:
        mail = mail_templates.get_mail_mypayment_device_activation(
            activation_url=f"{settings.CLIENT_URL}mypayment/devices/activate?token={activation_token}",
        )

        background_tasks.add_task(
            send_email,
            recipient=user.email,
            subject="MyECL - activate your device",
            content=mail,
            settings=settings,
        )
    else:
        hyperion_error_logger.warning(
            f"MyPayment: activate your device using the token: {activation_token}",
        )
    hyperion_mypayment_logger.info(
        wallet_device_creation.ed25519_public_key,
        extra={
            "s3_subfolder": f"{MYPAYMENT_DEVICES_S3_SUBFOLDER}/{user.id}",
            "s3_filename": str(wallet_device_db.id),
        },
    )

    return wallet_device_db


@router.get(
    "/mypayment/devices/activate",
    status_code=200,
)
async def activate_user_device(
    token: str,
    db: AsyncSession = Depends(get_db),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    settings: Settings = Depends(get_settings),
):
    """
    Activate a wallet device
    """

    wallet_device = await cruds_mypayment.get_wallet_device_by_activation_token(
        activation_token=token,
        db=db,
    )

    if wallet_device is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid token",
        )

    if wallet_device.status != WalletDeviceStatus.INACTIVE:
        return RedirectResponse(
            url=settings.CLIENT_URL
            + calypsso.get_message_relative_url(
                message_type=calypsso.TypeMessage.mypayment_wallet_device_already_activated_or_revoked,
            ),
        )

    await cruds_mypayment.update_wallet_device_status(
        wallet_device_id=wallet_device.id,
        status=WalletDeviceStatus.ACTIVE,
        db=db,
    )

    wallet = await cruds_mypayment.get_wallet(
        wallet_id=wallet_device.wallet_id,
        db=db,
    )
    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet does not exist",
        )

    user = wallet.user
    if user is not None:
        hyperion_error_logger.info(
            f"Wallet device {wallet_device.id} ({wallet_device.name}) activated by user {user.id}",
        )

        message = Message(
            title="💳 Paiement - appareil activé",
            content=f"Vous avez activé l'appareil {wallet_device.name}",
            action_module=settings.school.payment_name,
        )
        await notification_tool.send_notification_to_user(
            user_id=user.id,
            message=message,
        )
    else:
        raise UnexpectedError(f"Activated wallet device {wallet_device.id} has no user")  # noqa: TRY003

    return RedirectResponse(
        url=settings.CLIENT_URL
        + calypsso.get_message_relative_url(
            message_type=calypsso.TypeMessage.mypayment_wallet_device_activation_success,
        ),
    )


@router.post(
    "/mypayment/users/me/wallet/devices/{wallet_device_id}/revoke",
    status_code=204,
)
async def revoke_user_devices(
    wallet_device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    settings: Settings = Depends(get_settings),
):
    """
    Revoke a device for the user.

    **The user must be authenticated to use this endpoint**
    """
    # Check if user is already registered
    user_payment = await cruds_mypayment.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if user_payment is None or not is_user_latest_tos_signed(user_payment):
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    wallet_device = await cruds_mypayment.get_wallet_device(
        wallet_device_id=wallet_device_id,
        db=db,
    )

    if wallet_device is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet device does not exist",
        )

    if wallet_device.wallet_id != user_payment.wallet_id:
        raise HTTPException(
            status_code=400,
            detail="Wallet device does not belong to the user",
        )

    await cruds_mypayment.update_wallet_device_status(
        wallet_device_id=wallet_device_id,
        status=WalletDeviceStatus.REVOKED,
        db=db,
    )

    hyperion_error_logger.info(
        f"Wallet device {wallet_device.id} ({wallet_device.name}) revoked by user {user_payment.user_id}",
    )

    message = Message(
        title="💳 Paiement - appareil revoqué",
        content=f"Vous avez revoqué l'appareil {wallet_device.name}",
        action_module=settings.school.payment_name,
    )
    await notification_tool.send_notification_to_user(
        user_id=user_payment.user_id,
        message=message,
    )


@router.get(
    "/mypayment/users/me/wallet/history",
    response_model=list[schemas_mypayment.History],
)
async def get_user_wallet_history(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    """
    Get all transactions for the current user's wallet.

    **The user must be authenticated to use this endpoint**
    """
    user_payment = await cruds_mypayment.get_user_payment(
        user_id=user.id,
        db=db,
    )

    if user_payment is None:
        raise HTTPException(
            status_code=404,
            detail="User is not registered for MyECL Pay",
        )

    history: list[schemas_mypayment.History] = []

    # First we get all received and send transactions
    transactions = await cruds_mypayment.get_transactions_by_wallet_id(
        wallet_id=user_payment.wallet_id,
        db=db,
        start_datetime=start_date,
        end_datetime=end_date,
    )

    for transaction in transactions:
        if transaction.credited_wallet_id == user_payment.wallet_id:
            # The user received the transaction
            transaction_type = HistoryType.RECEIVED
            other_wallet = transaction.debited_wallet
        else:
            # The user sent the transaction
            transaction_type = HistoryType.GIVEN
            other_wallet = transaction.credited_wallet

        # We need to find if the other wallet correspond to a store or a user to get its display name
        if other_wallet.store is not None:
            other_wallet_name = other_wallet.store.name
        elif other_wallet.user is not None:
            other_wallet_name = other_wallet.user.full_name
        else:
            raise UnexpectedError("Transaction has no credited or debited wallet")  # noqa: TRY003

        history_refund: schemas_mypayment.HistoryRefund | None = None
        if transaction.refund is not None:
            history_refund = schemas_mypayment.HistoryRefund(
                total=transaction.refund.total,
                creation=transaction.refund.creation,
            )
        history.append(
            schemas_mypayment.History(
                id=transaction.id,
                type=transaction_type,
                other_wallet_name=other_wallet_name,
                total=transaction.total,
                creation=transaction.creation,
                status=transaction.status,
                refund=history_refund,
            ),
        )

    # We also want to include transfers
    transfers = await cruds_mypayment.get_transfers_by_wallet_id(
        wallet_id=user_payment.wallet_id,
        db=db,
        start_datetime=start_date,
        end_datetime=end_date,
    )

    for transfer in transfers:
        if transfer.confirmed:
            status = TransactionStatus.CONFIRMED
        elif datetime.now(UTC) < transfer.creation + timedelta(minutes=15):
            status = TransactionStatus.PENDING
        else:
            status = TransactionStatus.CANCELED

        history.append(
            schemas_mypayment.History(
                id=transfer.id,
                type=HistoryType.TRANSFER,
                other_wallet_name="Transfer",
                total=transfer.total,
                creation=transfer.creation,
                status=status,
            ),
        )

    # We add refunds
    refunds = await cruds_mypayment.get_refunds_by_wallet_id(
        wallet_id=user_payment.wallet_id,
        db=db,
        start_datetime=start_date,
        end_datetime=end_date,
    )
    for refund in refunds:
        if refund.debited_wallet_id == user_payment.wallet_id:
            transaction_type = HistoryType.REFUND_DEBITED
            other_wallet_info = refund.credited_wallet
        else:
            transaction_type = HistoryType.REFUND_CREDITED
            other_wallet_info = refund.debited_wallet

        history.append(
            schemas_mypayment.History(
                id=refund.id,
                type=transaction_type,
                other_wallet_name=other_wallet_info.owner_name or "Unknown",
                total=refund.total,
                creation=refund.creation,
                status=TransactionStatus.CONFIRMED,
            ),
        )

    return history


@router.post(
    "/mypayment/transfer/init",
    response_model=schemas_payment.PaymentUrl,
    status_code=201,
)
async def init_ha_transfer(
    transfer_info: schemas_mypayment.TransferInfo,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
    payment_tool: PaymentTool = Depends(
        get_payment_tool(HelloAssoConfigName.MYPAYMENT),
    ),
):
    """
    Initiate HelloAsso transfer, return a payment url to complete the transaction on HelloAsso website.
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

    user_payment = await cruds_mypayment.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if user_payment is None:
        raise HTTPException(
            status_code=404,
            detail="User is not registered for MyECL Pay",
        )

    if not is_user_latest_tos_signed(user_payment):
        raise HTTPException(
            status_code=400,
            detail="User has not signed the latest TOS",
        )

    wallet = await cruds_mypayment.get_wallet(
        wallet_id=user_payment.wallet_id,
        db=db,
    )
    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet does not exist",
        )
    if (
        wallet.balance + transfer_info.amount
        > settings.MYPAYMENT_MAXIMUM_WALLET_BALANCE
    ):
        raise HTTPException(
            status_code=403,
            detail="Wallet balance would exceed the maximum allowed balance",
        )

    user_schema = schemas_users.CoreUser(
        account_type=user.account_type,
        school_id=user.school_id,
        email=user.email,
        birthday=user.birthday,
        promo=user.promo,
        floor=user.floor,
        phone=user.phone,
        created_on=user.created_on,
        groups=[],
        id=user.id,
        name=user.name,
        firstname=user.firstname,
        nickname=user.nickname,
    )
    checkout = await payment_tool.init_checkout(
        module="mypayment",
        checkout_amount=transfer_info.amount,
        checkout_name=f"Recharge {settings.school.payment_name}",
        redirection_uri=f"{settings.CLIENT_URL}mypayment/transfer/redirect?url={transfer_info.redirect_url}",
        payer_user=user_schema,
        db=db,
    )

    await cruds_mypayment.create_transfer(
        db=db,
        transfer=schemas_mypayment.Transfer(
            id=uuid.uuid4(),
            type=TransferType.HELLO_ASSO,
            approver_user_id=None,
            total=transfer_info.amount,
            transfer_identifier=str(checkout.id),
            wallet_id=user_payment.wallet_id,
            creation=datetime.now(UTC),
            confirmed=False,
        ),
    )

    return schemas_payment.PaymentUrl(
        url=checkout.payment_url,
    )


@router.get(
    "/mypayment/transfer/redirect",
    response_model=schemas_payment.PaymentUrl,
    status_code=201,
)
async def redirect_from_ha_transfer(
    url: str,
    checkoutIntentId: str | None = None,
    code: str | None = None,
    orderId: str | None = None,
    error: str | None = None,
    settings: Settings = Depends(get_settings),
):
    """
    HelloAsso checkout should be configured to redirect the user to:
     - f"{settings.CLIENT_URL}mypayment/transfer/redirect?url={redirect_url}"
    Redirect the user to the provided redirect `url`. The parameters `checkoutIntentId`, `code`, `orderId` and `error` passed by HelloAsso will be added to the redirect URL.
    The redirect `url` must be trusted by Hyperion in the dotenv.
    """
    if url not in settings.TRUSTED_PAYMENT_REDIRECT_URLS:
        hyperion_error_logger.warning(
            f"Tried to redirect to an untrusted URL: {url}",
        )
        raise HTTPException(
            status_code=400,
            detail="Redirect URL is not trusted by hyperion",
        )

    params = {
        "checkoutIntentId": checkoutIntentId,
        "code": code,
        "orderId": orderId,
        "error": error,
    }

    encoded_params = urllib.parse.urlencode(
        {k: v for k, v in params.items() if v is not None},
    )

    parsed_url = urllib.parse.urlparse(url)._replace(query=encoded_params)

    return RedirectResponse(parsed_url.geturl())


@router.post(
    "/mypayment/stores/{store_id}/scan/check",
    response_model=standard_responses.Result,
    status_code=200,
)
async def validate_can_scan_qrcode(
    store_id: UUID,
    scan_info: schemas_mypayment.ScanInfo,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Validate if a given QR Code can be scanned by the seller.

    The QR Code should be valid, the seller should have the `can_bank` permission for this store,
    and the debited wallet device should be active.

    If the store structure has an association membership, the user should be a member of the association.

    **The user must be authenticated to use this endpoint**
    """
    store = await cruds_mypayment.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller = await cruds_mypayment.get_seller(
        store_id=store_id,
        user_id=user.id,
        db=db,
    )

    if seller is None or not seller.can_bank:
        raise HTTPException(
            status_code=400,
            detail="User does not have `can_bank` permission for this store",
        )

    debited_wallet_device = await cruds_mypayment.get_wallet_device(
        wallet_device_id=scan_info.key,
        db=db,
    )
    if debited_wallet_device is None:
        raise HTTPException(
            status_code=400,
            detail="Wallet device does not exist",
        )

    debited_wallet = await cruds_mypayment.get_wallet(
        wallet_id=debited_wallet_device.wallet_id,
        db=db,
    )
    if debited_wallet is None:
        hyperion_error_logger.error(
            f"MyPayment: Could not find wallet associated with the debited wallet device {debited_wallet_device.id}, this should never happen",
        )
        raise HTTPException(
            status_code=400,
            detail="Could not find wallet associated with the debited wallet device",
        )
    if debited_wallet.user is None:
        hyperion_error_logger.error(
            f"MyPayment: Debited wallet device {debited_wallet_device.id} does not contains a user, this should never happen",
        )
        raise HTTPException(
            status_code=400,
            detail="Wallet device does not contains a user",
        )

    if store.structure.association_membership_id:
        # We check if the user is a member of the association
        # and if the association membership is valid
        result = await get_user_active_membership_to_association_membership(
            user_id=debited_wallet.user.id,
            association_membership_id=store.structure.association_membership_id,
            db=db,
        )
        if result is None:
            return standard_responses.Result(success=False)

    return standard_responses.Result(success=True)


@router.post(
    "/mypayment/stores/{store_id}/scan",
    status_code=201,
)
async def store_scan_qrcode(
    store_id: UUID,
    scan_info: schemas_mypayment.ScanInfo,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
    request_id: str = Depends(get_request_id),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    settings: Settings = Depends(get_settings),
):
    """
    Scan and bank a QR code for this store.

    `signature` should be a base64 encoded string
     - signed using *ed25519*,
     - where data are a `QRCodeContentData` object:
        ```
        {
            id: UUID
            tot: int
            iat: datetime
            key: UUID
        }
        ```

    The provided content is checked to ensure:
        - the QR Code is not already used
        - the QR Code is not expired
        - the QR Code is intended to be scanned for a store `scan_info.store`
        - the signature is valid and correspond to `wallet_device_id` public key
        - the debited's wallet device is active
        - the debited's Wallet balance greater than the QR Code total

    **The user must be authenticated to use this endpoint**
    **The user must have the `can_bank` permission for this store**
    """
    # If the QR Code is already used, we return an error
    already_existing_used_qrcode = await cruds_mypayment.get_used_qrcode(
        qr_code_id=scan_info.id,
        db=db,
    )
    if already_existing_used_qrcode is not None:
        raise HTTPException(
            status_code=409,
            detail="QR Code already used",
        )

    # After scanning a QR Code, we want to add it to the list of already scanned QR Code
    # even if it fail to be banked
    await cruds_mypayment.create_used_qrcode(
        qr_code=scan_info,
        db=db,
    )

    await db.flush()

    # We start a SAVEPOINT to ensure that even if the following code fails due to a database exception,
    # after roleback the `used_qrcode` will still be created and committed in db.
    async with db.begin_nested():
        store = await cruds_mypayment.get_store(
            store_id=store_id,
            db=db,
        )
        if store is None:
            raise HTTPException(
                status_code=404,
                detail="Store does not exist",
            )

        seller = await cruds_mypayment.get_seller(
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
        debited_wallet_device = await cruds_mypayment.get_wallet_device(
            wallet_device_id=scan_info.key,
            db=db,
        )

        if debited_wallet_device is None:
            raise HTTPException(
                status_code=400,
                detail="Wallet device does not exist",
            )

        if debited_wallet_device.status != WalletDeviceStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail="Wallet device is not active",
            )

        if not verify_signature(
            public_key_bytes=debited_wallet_device.ed25519_public_key,
            signature=scan_info.signature,
            data=scan_info,
            wallet_device_id=scan_info.key,
            request_id=request_id,
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid signature",
            )

        if not scan_info.store:
            raise HTTPException(
                status_code=400,
                detail="QR Code is not intended to be scanned for a store",
            )

        # We verify the content respect some rules
        if scan_info.tot <= 0:
            raise HTTPException(
                status_code=400,
                detail="Total must be greater than 0",
            )

        if scan_info.iat < datetime.now(UTC) - timedelta(
            minutes=QRCODE_EXPIRATION,
        ):
            raise HTTPException(
                status_code=400,
                detail="QR Code is expired",
            )

        # We verify that the debited walled contains enough money
        debited_wallet = await cruds_mypayment.get_wallet(
            wallet_id=debited_wallet_device.wallet_id,
            db=db,
        )
        if debited_wallet is None:
            hyperion_error_logger.error(
                f"MyPayment: Could not find wallet associated with the debited wallet device {debited_wallet_device.id}, this should never happen",
            )
            raise HTTPException(
                status_code=400,
                detail="Could not find wallet associated with the debited wallet device",
            )
        if debited_wallet.user is None or debited_wallet.store is not None:
            raise HTTPException(
                status_code=400,
                detail="Stores are not allowed to make transaction by QR code",
            )

        debited_user_payment = await cruds_mypayment.get_user_payment(
            debited_wallet.user.id,
            db=db,
        )
        if debited_user_payment is None or not is_user_latest_tos_signed(
            debited_user_payment,
        ):
            raise HTTPException(
                status_code=400,
                detail="Debited user has not signed the latest TOS",
            )

        if debited_wallet.balance < scan_info.tot:
            raise HTTPException(
                status_code=400,
                detail="Insufficient balance in the debited wallet",
            )

        # If `bypass_membership` is not set, we check if the user is a member of the association
        # and raise an error if not
        if not scan_info.bypass_membership:
            if store.structure.association_membership_id is not None:
                current_membership = await get_user_active_membership_to_association_membership(
                    user_id=debited_wallet.user.id,
                    association_membership_id=store.structure.association_membership_id,
                    db=db,
                )
                if current_membership is None:
                    raise HTTPException(
                        status_code=400,
                        detail="User is not a member of the association",
                    )

        # We increment the receiving wallet balance
        await cruds_mypayment.increment_wallet_balance(
            wallet_id=store.wallet_id,
            amount=scan_info.tot,
            db=db,
        )

        # We decrement the debited wallet balance
        await cruds_mypayment.increment_wallet_balance(
            wallet_id=debited_wallet.id,
            amount=-scan_info.tot,
            db=db,
        )
        transaction_id = uuid.uuid4()
        creation_date = datetime.now(UTC)
        transaction = schemas_mypayment.TransactionBase(
            id=transaction_id,
            debited_wallet_id=debited_wallet_device.wallet_id,
            credited_wallet_id=store.wallet_id,
            transaction_type=TransactionType.DIRECT,
            seller_user_id=user.id,
            total=scan_info.tot,
            creation=creation_date,
            status=TransactionStatus.CONFIRMED,
            qr_code_id=scan_info.id,
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
            content=f"Une transaction de {scan_info.tot / 100} € a été effectuée",
            action_module=settings.school.payment_name,
        )
        await notification_tool.send_notification_to_user(
            user_id=debited_wallet.user.id,
            message=message,
        )
        return transaction


@router.post(
    "/mypayment/transactions/{transaction_id}/refund",
    status_code=204,
)
async def refund_transaction(
    transaction_id: UUID,
    refund_info: schemas_mypayment.RefundInfo,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    settings: Settings = Depends(get_settings),
):
    """
    Refund a transaction. Only transactions made in the last 30 days can be refunded.

    Currently transactions between users are forbidden and can thus not be refunded.

    To cancel a transaction made in the last 30 seconds, the endpoint `/mypayment/transactions/{transaction_id}/cancel` should be used.

    **The user must either be the credited user or a seller with cancel permissions of the credited store of the transaction**
    """
    transaction = await cruds_mypayment.get_transaction(
        transaction_id=transaction_id,
        db=db,
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction does not exist",
        )

    if transaction.status != TransactionStatus.CONFIRMED:
        raise HTTPException(
            status_code=400,
            detail="Transaction is not available for refund",
        )

    if transaction.creation <= datetime.now(UTC) - timedelta(days=30):
        raise HTTPException(
            status_code=400,
            detail="Transaction older than 30 days can not be refunded",
        )

    # The wallet that was credited if the one that will be de debited during the refund
    wallet_previously_credited = await cruds_mypayment.get_wallet(
        wallet_id=transaction.credited_wallet_id,
        db=db,
    )
    if wallet_previously_credited is None:
        raise HTTPException(
            status_code=404,
            detail="Credited wallet that need to refund the transaction does not exist",
        )

    if wallet_previously_credited.type == WalletType.STORE:
        if wallet_previously_credited.store is None:
            raise HTTPException(
                status_code=404,
                detail="Missing store in store wallet",
            )
        seller = await cruds_mypayment.get_seller(
            store_id=wallet_previously_credited.store.id,
            user_id=user.id,
            db=db,
        )
        if seller is None or not seller.can_cancel:
            raise HTTPException(
                status_code=403,
                detail="User does not have the permission to refund this transaction",
            )
        wallet_previously_credited_name = wallet_previously_credited.store.name
    else:
        # Currently transaction between users are forbidden
        raise HTTPException(
            status_code=403,
            detail="Transaction credited to a user can not be refunded",
        )
        # if wallet_previously_credited.user is None:
        #     raise HTTPException(
        #         status_code=404,
        #         detail="User does not exist",
        #     )
        # if wallet_previously_credited.user.id != user.id:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="User is not allowed to refund this transaction",
        #     )
        # wallet_previously_credited_name = wallet_previously_credited.user.full_name

    if refund_info.complete_refund:
        refund_amount = transaction.total
    else:
        if refund_info.amount is None:
            raise HTTPException(
                status_code=400,
                detail="Please provide an amount for the refund if it is not a complete refund",
            )
        if refund_info.amount > transaction.total:
            raise HTTPException(
                status_code=400,
                detail="Refund amount is greater than the transaction total",
            )
        if refund_info.amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Refund amount must be greater than 0",
            )
        refund_amount = refund_info.amount

    # The wallet that was debited is the one that will be credited during the refund
    wallet_previously_debited = await cruds_mypayment.get_wallet(
        wallet_id=transaction.debited_wallet_id,
        db=db,
    )
    if wallet_previously_debited is None:
        raise HTTPException(
            status_code=404,
            detail="The wallet that should be credited during the refund does not exist",
        )

    await cruds_mypayment.update_transaction_status(
        transaction_id=transaction_id,
        status=TransactionStatus.REFUNDED,
        db=db,
    )

    creation_date = datetime.now(UTC)
    refund = schemas_mypayment.RefundBase(
        id=uuid.uuid4(),
        transaction_id=transaction_id,
        total=refund_amount,
        seller_user_id=user.id
        if wallet_previously_credited.type == WalletType.STORE
        else None,
        credited_wallet_id=wallet_previously_debited.id,
        debited_wallet_id=wallet_previously_credited.id,
        creation=creation_date,
    )

    await cruds_mypayment.create_refund(
        refund=refund,
        db=db,
    )

    # We add the amount to the wallet that was previously debited
    await cruds_mypayment.increment_wallet_balance(
        wallet_id=wallet_previously_debited.id,
        amount=refund_amount,
        db=db,
    )

    await cruds_mypayment.increment_wallet_balance(
        wallet_id=wallet_previously_credited.id,
        amount=-refund_amount,
        db=db,
    )

    hyperion_mypayment_logger.info(
        format_refund_log(refund),
        extra={
            "s3_subfolder": MYPAYMENT_LOGS_S3_SUBFOLDER,
            "s3_retention": RETENTION_DURATION,
        },
    )

    if wallet_previously_debited.user is not None:
        message = Message(
            title="💳 Remboursement",
            content=f"La transaction pour {wallet_previously_credited_name} ({transaction.total / 100} €) a été remboursée de {refund_amount / 100} €",
            action_module=settings.school.payment_name,
        )
        await notification_tool.send_notification_to_user(
            user_id=wallet_previously_debited.user.id,
            message=message,
        )

    if wallet_previously_credited.user is not None:
        if wallet_previously_debited.user is not None:
            wallet_previously_debited_name = wallet_previously_debited.user.full_name
        elif wallet_previously_debited.store is not None:
            wallet_previously_debited_name = wallet_previously_debited.store.name
        message = Message(
            title="💳 Remboursement",
            content=f"Vous avez remboursé la transaction de {wallet_previously_debited_name} ({transaction.total / 100} €) de {refund_amount / 100} €",
            action_module=settings.school.payment_name,
        )
        await notification_tool.send_notification_to_user(
            user_id=wallet_previously_credited.user.id,
            message=message,
        )


@router.post(
    "/mypayment/transactions/{transaction_id}/cancel",
    status_code=204,
)
async def cancel_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
    request_id: str = Depends(get_request_id),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    settings: Settings = Depends(get_settings),
):
    """
    Cancel a transaction.
    A transaction can be canceled in the first 30 seconds after it has been created.

    To refund an older transaction, use the `/mypayment/transactions/{transaction_id}/refund` endpoint.

    **The user must either be the credited user or the seller of the transaction**
    """
    transaction = await cruds_mypayment.get_transaction(
        transaction_id=transaction_id,
        db=db,
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction does not exist",
        )

    if datetime.now(UTC) - transaction.creation > timedelta(seconds=30):
        raise HTTPException(
            status_code=400,
            detail="Transaction is older than 30 seconds and can not be canceled",
        )

    canceller_wallet = await cruds_mypayment.get_wallet(
        wallet_id=transaction.credited_wallet_id,
        db=db,
    )
    if canceller_wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Credited wallet does not exist",
        )

    if canceller_wallet.type == WalletType.STORE:
        if canceller_wallet.store is None:
            raise HTTPException(
                status_code=404,
                detail="Store does not exist",
            )
        seller = await cruds_mypayment.get_seller(
            store_id=canceller_wallet.store.id,
            user_id=user.id,
            db=db,
        )
        if seller is None:
            raise HTTPException(
                status_code=403,
                detail="User does not have the permission to cancel this transaction",
            )

        if not seller.can_cancel:
            raise HTTPException(
                status_code=400,
                detail="User does not have the permission to cancel this transaction",
            )

    else:
        if canceller_wallet.user is None:
            raise HTTPException(
                status_code=404,
                detail="User does not exist",
            )
        if canceller_wallet.user.id != user.id:
            raise HTTPException(
                status_code=403,
                detail="User is not allowed to cancel this transaction",
            )

    if transaction.status != TransactionStatus.CONFIRMED:
        raise HTTPException(
            status_code=400,
            detail="Only confirmed transactions can be canceled",
        )

    debited_wallet = await cruds_mypayment.get_wallet(
        wallet_id=transaction.debited_wallet_id,
        db=db,
    )
    if debited_wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Debited wallet does not exist",
        )

    await cruds_mypayment.update_transaction_status(
        transaction_id=transaction_id,
        status=TransactionStatus.CANCELED,
        db=db,
    )

    await cruds_mypayment.increment_wallet_balance(
        wallet_id=transaction.debited_wallet_id,
        amount=transaction.total,
        db=db,
    )

    await cruds_mypayment.increment_wallet_balance(
        wallet_id=transaction.credited_wallet_id,
        amount=-transaction.total,
        db=db,
    )

    hyperion_mypayment_logger.info(
        format_cancel_log(transaction_id),
        extra={
            "s3_subfolder": MYPAYMENT_LOGS_S3_SUBFOLDER,
            "s3_retention": RETENTION_DURATION,
        },
    )

    if debited_wallet.user is not None:
        message = Message(
            title="💳 Paiement annulé",
            content=f"La transaction de {transaction.total / 100} € a été annulée",
            action_module=settings.school.payment_name,
        )
        await notification_tool.send_notification_to_user(
            user_id=debited_wallet.user.id,
            message=message,
        )


@router.get(
    "/mypayment/invoices",
    response_model=list[schemas_mypayment.Invoice],
)
async def get_invoices(
    page: int | None = None,
    page_size: int | None = None,
    structures_ids: list[UUID] | None = Query(default=None),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_bank_account_holder),
) -> list[schemas_mypayment.Invoice]:
    """
    Get all invoices.

    **The user must be authenticated to use this endpoint**
    """
    return await cruds_mypayment.get_invoices(
        db=db,
        skip=(page - 1) * page_size if page and page_size else None,
        limit=page_size,
        start_date=start_date,
        end_date=end_date,
        structures_ids=structures_ids,
    )


@router.get(
    "/mypayment/invoices/structures/{structure_id}",
    response_model=list[schemas_mypayment.Invoice],
)
async def get_structure_invoices(
    structure_id: UUID,
    page: int | None = None,
    page_size: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
) -> list[schemas_mypayment.Invoice]:
    """
    Get all invoices.

    **The user must be the structure manager**
    """
    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )
    if structure.manager_user_id != user.id and user.id not in [
        admin.id for admin in structure.administrators
    ]:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to access this structure invoices",
        )

    return await cruds_mypayment.get_invoices(
        db=db,
        skip=(page - 1) * page_size if page and page_size else None,
        limit=page_size,
        start_date=start_date,
        end_date=end_date,
        structures_ids=[structure_id],
    )


@router.get(
    "/mypayment/invoices/{invoice_id}",
    response_class=FileResponse,
)
async def download_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    invoice = await cruds_mypayment.get_invoice_by_id(invoice_id, db)
    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice does not exist",
        )
    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=invoice.structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )
    bank_account_info = await get_bank_account_holder(
        user=user,
        db=db,
    )
    if user.id not in (
        structure.manager_user_id,
        bank_account_info.manager_user_id,
        *[admin.id for admin in structure.administrators],
    ):
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to access this invoice",
        )
    return get_file_from_data(
        directory="mypayment/invoices",
        filename=str(invoice_id),
    )


@router.post(
    "/mypayment/invoices/structures/{structure_id}",
    response_model=schemas_mypayment.Invoice,
    status_code=201,
)
async def create_structure_invoice(
    structure_id: UUID,
    db: AsyncSession = Depends(get_db),
    token_data: schemas_auth.TokenData = Depends(get_token_data),
    settings: Settings = Depends(get_settings),
):
    """
    Create an invoice for a structure.

    **The user must be the bank account holder**
    """
    now = await cruds_core.start_isolation_mode(db)
    # Database isolation requires to be the first statement of the transaction
    # We can't use reguler dependencies to check user permissions as they access the database
    user_id = get_user_id_from_token_with_scopes(
        scopes=[[ScopeType.API]],
        token_data=token_data,
    )
    user = await cruds_users.get_user_by_id(
        db=db,
        user_id=user_id,
    )
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User does not exist",
        )
    bank_holder_structure = await get_bank_account_holder(
        user=user,
        db=db,
    )
    if bank_holder_structure.manager_user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="User is not the bank account holder",
        )
    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )

    stores = await cruds_mypayment.get_stores_by_structure_id(
        structure_id=structure_id,
        db=db,
    )
    invoice_details: list[schemas_mypayment.InvoiceDetailBase] = []
    invoice_id = uuid.uuid4()

    # We use a 30 seconds delay to avoid unstable transactions
    # as they can be canceled during the 30 seconds after their creation
    security_now = now - timedelta(seconds=30)
    to_substract_transactions = await cruds_mypayment.get_transactions(
        db=db,
        start_date=security_now,
        exclude_canceled=True,
    )

    for store in stores:
        store_wallet_db = await cruds_mypayment.get_wallet(
            wallet_id=store.wallet_id,
            db=db,
        )
        if store_wallet_db is None:
            hyperion_error_logger.error(
                "MyPayment: Could not find wallet associated with a store, this should never happen",
            )
            raise HTTPException(
                status_code=500,
                detail="Could not find wallet associated with the store",
            )
        store_wallet = schemas_mypayment.Wallet(
            id=store_wallet_db.id,
            type=store_wallet_db.type,
            balance=store_wallet_db.balance,
            user=None,
            store=None,
        )
        for transaction in to_substract_transactions:
            if transaction.credited_wallet_id == store_wallet.id:
                store_wallet.balance -= transaction.total
            elif transaction.debited_wallet_id == store_wallet.id:
                store_wallet.balance += transaction.total
        store_pending_invoices = (
            await cruds_mypayment.get_unreceived_invoices_by_store_id(
                store_id=store.id,
                db=db,
            )
        )
        for pending_invoice in store_pending_invoices:
            store_wallet.balance -= pending_invoice.total
        if store_wallet.balance != 0:
            invoice_details.append(
                schemas_mypayment.InvoiceDetailBase(
                    invoice_id=invoice_id,
                    store_id=store.id,
                    total=store_wallet.balance,
                ),
            )
    if not invoice_details:
        raise HTTPException(
            status_code=400,
            detail="No invoice to create",
        )
    last_structure_invoice = await cruds_mypayment.get_last_structure_invoice(
        structure_id=structure_id,
        db=db,
    )
    if last_structure_invoice:
        year, last_invoice_number = re.findall(
            r"[a-zA-Z]*(\d{4})[a-zA-Z]*(\d{4})",
            last_structure_invoice.reference,
        )[0]
        last_invoice_number = int(last_invoice_number)
        year = int(year)
        if int(year) != security_now.year:
            last_invoice_number = 0
    else:
        last_invoice_number = 0
    invoice = schemas_mypayment.InvoiceInfo(
        id=invoice_id,
        reference=f"PAY{security_now.year}{structure.short_id}{last_invoice_number + 1:04d}",
        structure_id=structure_id,
        creation=datetime.now(UTC),
        start_date=last_structure_invoice.end_date
        if last_structure_invoice
        else structure.creation,
        end_date=security_now,
        total=sum(detail.total for detail in invoice_details),
        details=invoice_details,
    )
    await cruds_mypayment.create_invoice(
        invoice=invoice,
        db=db,
    )
    invoice_db = await cruds_mypayment.get_invoice_by_id(
        invoice_id=invoice_id,
        db=db,
    )
    if invoice_db is None:
        raise InvoiceNotFoundAfterCreationError(invoice_id=invoice_id)

    context = {
        "invoice": invoice_db.model_dump(),
        "payment_name": settings.school.payment_name,
        "holder_coordinates": {
            "name": bank_holder_structure.name,
            "address_street": bank_holder_structure.siege_address_street,
            "address_city": bank_holder_structure.siege_address_city,
            "address_zipcode": bank_holder_structure.siege_address_zipcode,
            "address_country": bank_holder_structure.siege_address_country,
            "siret": bank_holder_structure.siret,
        },
    }
    await generate_pdf_from_template(
        template_name="mypayment_invoice.html",
        directory="mypayment/invoices",
        filename=invoice.id,
        context=context,
    )
    return invoice_db


@router.patch(
    "/mypayment/invoices/{invoice_id}/paid",
    status_code=204,
)
async def update_invoice_paid_status(
    invoice_id: UUID,
    paid: bool,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_bank_account_holder),
):
    """
    Update the paid status of a structure invoice.

    **The user must be the bank account holder**
    """
    hyperion_error_logger.debug(
        f"User {user.id} requested to update the paid status of invoice {invoice_id} to {paid}",
    )
    invoice = await cruds_mypayment.get_invoice_by_id(
        invoice_id=invoice_id,
        db=db,
    )
    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice does not exist",
        )
    await cruds_mypayment.update_invoice_paid_status(
        invoice_id=invoice.id,
        paid=paid,
        db=db,
    )


@router.patch(
    "/mypayment/invoices/{invoice_id}/received",
    status_code=204,
)
async def aknowledge_invoice_as_received(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Update the received status of a structure invoice.

    **The user must be the structure manager**
    """
    invoice = await cruds_mypayment.get_invoice_by_id(
        invoice_id=invoice_id,
        db=db,
    )
    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice does not exist",
        )
    if not invoice.paid:
        raise HTTPException(
            status_code=400,
            detail="Cannot mark an invoice as received if it is not paid",
        )
    if invoice.received:
        raise HTTPException(
            status_code=400,
            detail="Invoice is already marked as received",
        )
    structure = await cruds_mypayment.get_structure_by_id(
        structure_id=invoice.structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=500,
            detail="Structure does not exist",
        )
    if structure.manager_user_id != user.id and user.id not in [
        admin.id for admin in structure.administrators
    ]:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to edit this structure invoice",
        )

    await cruds_mypayment.update_invoice_received_status(
        invoice_id=invoice.id,
        db=db,
    )
    for detail in invoice.details:
        store = await cruds_mypayment.get_store(
            store_id=detail.store_id,
            db=db,
        )
        if store is None:
            hyperion_error_logger.error(
                "MyPayment: Could not find store associated with an invoice, this should never happen",
            )
            raise HTTPException(
                status_code=500,
                detail="Could not find store associated with the invoice",
            )
        await cruds_mypayment.increment_wallet_balance(
            wallet_id=store.wallet_id,
            amount=-detail.total,
            db=db,
        )
        await cruds_mypayment.add_withdrawal(
            schemas_mypayment.Withdrawal(
                id=uuid.uuid4(),
                wallet_id=store.wallet_id,
                total=detail.total,
                creation=datetime.now(UTC),
            ),
            db=db,
        )

        hyperion_mypayment_logger.info(
            format_withdrawal_log(
                wallet_id=store.wallet_id,
                total=detail.total,
            ),
            extra={
                "s3_subfolder": MYPAYMENT_LOGS_S3_SUBFOLDER,
                "s3_retention": RETENTION_DURATION,
            },
        )


@router.delete(
    "/mypayment/invoices/{invoice_id}",
    status_code=204,
)
async def delete_structure_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_bank_account_holder),
):
    """
    Delete a structure invoice.

    **The user must be the bank account holder**
    """
    invoice = await cruds_mypayment.get_invoice_by_id(
        invoice_id=invoice_id,
        db=db,
    )
    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice does not exist",
        )
    if invoice.paid:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an invoice that has already been paid",
        )

    await cruds_mypayment.delete_invoice(
        invoice_id=invoice.id,
        db=db,
    )


@router.get(
    "/mypayment/integrity-check",
    status_code=200,
    response_model=schemas_mypayment.IntegrityCheckData,
)
async def get_data_for_integrity_check(
    headers: schemas_mypayment.IntegrityCheckHeaders = Header(),
    query_params: schemas_mypayment.IntegrityCheckQuery = Query(),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Send all the MyECL Pay data for integrity check.
    Data includes:
    - Wallets deducted of the last 30 seconds transactions
    - Transactions with at least 30 seconds delay
    - Transfers
    - Refunds

    **The header must contain the MYPAYMENT_DATA_VERIFIER_ACCESS_TOKEN defined in the settings in the `x-data-verifier-token` field**
    """
    if settings.MYPAYMENT_DATA_VERIFIER_ACCESS_TOKEN is None:
        raise HTTPException(
            status_code=301,
            detail="MYPAYMENT_DATA_VERIFIER_ACCESS_TOKEN is not set in the settings",
        )

    if headers.x_data_verifier_token != settings.MYPAYMENT_DATA_VERIFIER_ACCESS_TOKEN:
        hyperion_security_logger.warning(
            f"A request to /mypayment/integrity-check has been made with an invalid token, request_content: {headers}",
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    now = await cruds_core.start_isolation_mode(db)
    # We use a 30 seconds delay to avoid unstable transactions
    # as they can be canceled during the 30 seconds after their creation
    security_now = now - timedelta(seconds=30)

    wallets = await cruds_mypayment.get_wallets(
        db=db,
    )
    to_substract_transactions = await cruds_mypayment.get_transactions(
        db=db,
        start_date=security_now,
        exclude_canceled=True,
    )
    # We substract the transactions that are not older than 30 seconds
    for transaction in to_substract_transactions:
        debited_wallet = next(
            (w for w in wallets if w.id == transaction.debited_wallet_id),
            None,
        )
        credited_wallet = next(
            (w for w in wallets if w.id == transaction.credited_wallet_id),
            None,
        )
        if debited_wallet is not None:
            debited_wallet.balance += transaction.total
        if credited_wallet is not None:
            credited_wallet.balance -= transaction.total

    if query_params.isInitialisation:
        return schemas_mypayment.IntegrityCheckData(
            date=security_now,
            wallets=wallets,
            transactions=[],
            transfers=[],
            refunds=[],
        )
    transactions = await cruds_mypayment.get_transactions(
        db=db,
        start_date=query_params.lastChecked,
        end_date=security_now,
    )
    transfers = await cruds_mypayment.get_transfers(
        db=db,
        last_checked=query_params.lastChecked,
    )
    refunds = await cruds_mypayment.get_refunds(
        db=db,
        last_checked=query_params.lastChecked,
    )

    return schemas_mypayment.IntegrityCheckData(
        date=security_now,
        wallets=wallets,
        transactions=transactions,
        transfers=transfers,
        refunds=refunds,
    )
