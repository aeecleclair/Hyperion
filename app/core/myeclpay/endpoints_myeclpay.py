import logging
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import BackgroundTasks, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import schemas_core, security
from app.core.config import Settings
from app.core.groups.groups_type import AccountType, GroupType
from app.core.models_core import CoreUser
from app.core.myeclpay import cruds_myeclpay, schemas_myeclpay
from app.core.myeclpay.models_myeclpay import Store, WalletDevice
from app.core.myeclpay.types_myeclpay import (
    HistoryType,
    TransactionStatus,
    TransactionType,
    TransferType,
    WalletDeviceStatus,
    WalletType,
)
from app.core.myeclpay.utils_myeclpay import (
    LATEST_TOS,
    MAX_TRANSACTION_TOTAL,
    QRCODE_EXPIRATION,
    TOS_CONTENT,
    compute_signable_data,
    is_user_latest_tos_signed,
    validate_transfer,
    verify_signature,
)
from app.core.notification.schemas_notification import Message
from app.core.payment import cruds_payment, schemas_payment
from app.core.payment.payment_tool import PaymentTool
from app.core.users import cruds_users
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_payment_tool,
    get_request_id,
    get_settings,
    is_user,
    is_user_an_ecl_member,
    is_user_in,
)
from app.types.module import Module
from app.utils.communication.notifications import NotificationTool
from app.utils.mail.mailworker import send_email
from app.utils.tools import get_display_name

module = Module(
    root="myeclpay",
    tag="MyECLPay",
    payment_callback=validate_transfer,
    default_allowed_account_types=list(AccountType),
)

templates = Jinja2Templates(directory="assets/templates")


hyperion_error_logger = logging.getLogger("hyperion.error")
hyperion_security_logger = logging.getLogger("hyperion.security")


@module.router.get(
    "/myeclpay/structures",
    status_code=200,
    response_model=list[schemas_myeclpay.Structure],
)
async def get_structures(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get all structures.
    """
    structures = await cruds_myeclpay.get_structures(
        db=db,
    )

    return structures


@module.router.post(
    "/myeclpay/structures",
    status_code=201,
    response_model=schemas_myeclpay.Structure,
)
async def create_structure(
    structure: schemas_myeclpay.StructureBase,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new structure.

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
    structure_db = schemas_myeclpay.Structure(
        id=uuid.uuid4(),
        name=structure.name,
        manager_user_id=structure.manager_user_id,
        manager_user=schemas_core.CoreUserSimple(
            id=db_user.id,
            name=db_user.name,
            firstname=db_user.firstname,
            nickname=db_user.nickname,
            account_type=db_user.account_type,
            school_id=db_user.school_id,
        ),
    )
    await cruds_myeclpay.create_structure(
        structure=structure_db,
        db=db,
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise

    return structure_db


@module.router.patch(
    "/myeclpay/structures/{structure_id}",
    status_code=204,
)
async def update_structure(
    structure_id: UUID,
    structure_update: schemas_myeclpay.StructureUpdate,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Update a structure.

    **The user must be an admin to use this endpoint**
    """
    await cruds_myeclpay.update_structure(
        structure_id=structure_id,
        structure_update=structure_update,
        db=db,
    )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


@module.router.delete(
    "/myeclpay/structures/{structure_id}",
    status_code=204,
)
async def delete_structure(
    structure_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a structure.

    **The user must be an admin to use this endpoint**
    """
    stores = await cruds_myeclpay.get_stores_by_structure_id(
        structure_id=structure_id,
        db=db,
    )
    if stores:
        raise HTTPException(
            status_code=400,
            detail="Structure has stores",
        )

    await cruds_myeclpay.delete_structure(
        structure_id=structure_id,
        db=db,
    )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


@module.router.post(
    "/myeclpay/structures/{structure_id}/init-manager-transfer",
    status_code=201,
)
async def init_update_structure_manager(
    structure_id: UUID,
    transfer_info: schemas_myeclpay.StructureTranfert,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
):
    """
    Initiate the update of a manager for an association

    **The user must be the manager for this structure**
    """
    structure = await cruds_myeclpay.get_structure_by_id(
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

    user_db = await cruds_users.get_user_by_id(
        user_id=transfer_info.new_manager_user_id,
        db=db,
    )
    if user_db is None:
        raise HTTPException(
            status_code=404,
            detail="User does not exist",
        )

    await cruds_myeclpay.delete_structure_manager_transfer_by_structure(
        structure_id=structure_id,
        db=db,
    )

    confirmation_token = security.generate_token()

    await cruds_myeclpay.init_structure_manager_transfer(
        structure_id=structure_id,
        user_id=transfer_info.new_manager_user_id,
        confirmation_token=confirmation_token,
        valid_until=datetime.now(tz=UTC)
        + timedelta(minutes=settings.MYECLPAY_MANAGER_TRANSFER_TOKEN_EXPIRES_MINUTES),
        db=db,
    )

    if settings.SMTP_ACTIVE:
        migration_content = templates.get_template(
            "structure_manager_transfer.html",
        ).render(
            {
                "transfer_link": f"{settings.CLIENT_URL}myeclpay/structures/manager/confirm-transfer?token={confirmation_token}",
            },
        )
        background_tasks.add_task(
            send_email,
            recipient=user_db.email,
            subject="MyECL - Confirm the structure manager transfer",
            content=migration_content,
            settings=settings,
        )
    else:
        hyperion_security_logger.info(
            f"You can confirm the transfer by clicking the following link: {settings.CLIENT_URL}myeclpay/structures/manager/confirm-transfer?token={confirmation_token}",
        )


@module.router.get(
    "/myeclpay/structures/confirm-manager-transfer",
    status_code=200,
)
async def update_structure_manager(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a manager for an association

    The user must have initiated the update of the manager with `init_update_structure_manager`
    """

    request = await cruds_myeclpay.get_structure_manager_transfer_by_secret(
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

    await cruds_myeclpay.update_structure_manager(
        structure_id=request.structure_id,
        manager_user_id=request.user_id,
        db=db,
    )

    stores = await cruds_myeclpay.get_stores_by_structure_id(
        structure_id=request.structure_id,
        db=db,
    )
    sellers = await cruds_myeclpay.get_sellers_by_user_id(
        user_id=request.user_id,
        db=db,
    )
    sellers_store_ids = [seller.store_id for seller in sellers]
    for store in stores:
        if store.id not in sellers_store_ids:
            await cruds_myeclpay.create_seller(
                user_id=request.user_id,
                store_id=store.id,
                can_bank=True,
                can_see_history=True,
                can_cancel=True,
                can_manage_sellers=True,
                db=db,
            )
        else:
            await cruds_myeclpay.update_seller(
                seller_user_id=request.user_id,
                store_id=store.id,
                can_bank=True,
                can_see_history=True,
                can_cancel=True,
                can_manage_sellers=True,
                db=db,
            )
    await db.commit()


@module.router.post(
    "/myeclpay/structures/{structure_id}/stores",
    status_code=201,
    response_model=schemas_myeclpay.Store,
)
async def create_store(
    structure_id: UUID,
    store: schemas_myeclpay.StoreBase,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Create a store

    **The user must be the manager for this structure**
    """
    structure = await cruds_myeclpay.get_structure_by_id(
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

    # Create new wallet for store
    wallet_id = uuid.uuid4()
    await cruds_myeclpay.create_wallet(
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
    )
    await cruds_myeclpay.create_store(
        store=store_db,
        db=db,
    )
    await db.commit()
    # Add manager as an full right seller for the store
    await cruds_myeclpay.create_seller(
        user_id=user.id,
        store_id=store_db.id,
        can_bank=True,
        can_see_history=True,
        can_cancel=True,
        can_manage_sellers=True,
        db=db,
    )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise

    return schemas_myeclpay.Store(
        id=store_db.id,
        name=store_db.name,
        structure_id=store_db.structure_id,
        wallet_id=store_db.wallet_id,
        structure=structure,
    )


@module.router.get(
    "/myeclpay/stores/{store_id}/history",
    status_code=200,
    response_model=list[schemas_myeclpay.Transaction],
)
async def get_store_history(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get all transactions for the store.

    **The user must be authorized to see the store history**
    """
    store = await cruds_myeclpay.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller = await cruds_myeclpay.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller is None or not seller.can_see_history:
        raise HTTPException(
            status_code=403,
            detail="User is not authorized to see the store history",
        )

    transactions = await cruds_myeclpay.get_transactions_by_wallet_id(
        wallet_id=store.wallet_id,
        db=db,
    )

    return transactions


@module.router.get(
    "/myeclpay/users/me/stores",
    status_code=200,
    response_model=list[schemas_myeclpay.UserStore],
)
async def get_user_stores(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get all stores for the current user.

    **The user must be authenticated to use this endpoint**
    """
    sellers = await cruds_myeclpay.get_sellers_by_user_id(
        user_id=user.id,
        db=db,
    )

    stores: list[schemas_myeclpay.UserStore] = []
    for seller in sellers:
        store = await cruds_myeclpay.get_store(
            store_id=seller.store_id,
            db=db,
        )
        if store is not None:
            stores.append(
                schemas_myeclpay.UserStore(
                    id=store.id,
                    name=store.name,
                    structure_id=store.structure_id,
                    structure=schemas_myeclpay.Structure(
                        id=store.structure.id,
                        name=store.structure.name,
                        manager_user_id=store.structure.manager_user_id,
                        manager_user=schemas_core.CoreUserSimple(
                            id=store.structure.manager_user.id,
                            name=store.structure.manager_user.name,
                            firstname=store.structure.manager_user.firstname,
                            nickname=store.structure.manager_user.nickname,
                            account_type=store.structure.manager_user.account_type,
                            school_id=store.structure.manager_user.school_id,
                        ),
                    ),
                    wallet_id=store.wallet_id,
                    can_bank=seller.can_bank,
                    can_see_history=seller.can_see_history,
                    can_cancel=seller.can_cancel,
                    can_manage_sellers=seller.can_manage_sellers,
                ),
            )

    return stores


@module.router.patch(
    "/myeclpay/stores/{store_id}",
    status_code=204,
)
async def update_store(
    store_id: UUID,
    store_update: schemas_myeclpay.StoreUpdate,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Update a store

    **The user must be the manager for this store's structure**
    """
    store = await cruds_myeclpay.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    structure = await cruds_myeclpay.get_structure_by_id(
        structure_id=store.structure_id,
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

    await cruds_myeclpay.update_store(
        store_id=store_id,
        store_update=store_update,
        db=db,
    )

    await db.commit()


@module.router.delete(
    "/myeclpay/stores/{store_id}",
    status_code=204,
)
async def delete_store(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Delete a store

    **The user must be the manager for this store's structure**
    """
    store = await cruds_myeclpay.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    structure = await cruds_myeclpay.get_structure_by_id(
        structure_id=store.structure_id,
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

    transactions = await cruds_myeclpay.get_transactions_by_wallet_id(
        wallet_id=store.wallet_id,
        db=db,
    )
    if transactions:
        raise HTTPException(
            status_code=400,
            detail="Store has transactions and cannot be deleted anymore",
        )

    sellers = await cruds_myeclpay.get_sellers_by_store_id(
        store_id=store_id,
        db=db,
    )
    for seller in sellers:
        await cruds_myeclpay.delete_seller(
            seller_user_id=seller.user_id,
            store_id=store_id,
            db=db,
        )

    await cruds_myeclpay.delete_store(
        store_id=store_id,
        db=db,
    )

    await db.commit()


@module.router.post(
    "/myeclpay/stores/{store_id}/sellers",
    status_code=201,
    response_model=schemas_myeclpay.Seller,
)
async def create_store_seller(
    store_id: UUID,
    seller: schemas_myeclpay.SellerCreation,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Create a store seller.

    This seller will have autorized permissions among:
    - can_bank
    - can_see_history
    - can_cancel
    - can_manage_sellers

    **The user must have the `can_manage_sellers` permission for this store**
    """
    store = await cruds_myeclpay.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller_admin = await cruds_myeclpay.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller_admin is None or not seller_admin.can_manage_sellers:
        raise HTTPException(
            status_code=403,
            detail="User does not have the permission to manage sellers",
        )

    await cruds_myeclpay.create_seller(
        user_id=seller.user_id,
        store_id=store_id,
        can_bank=seller.can_bank,
        can_see_history=seller.can_see_history,
        can_cancel=seller.can_cancel,
        can_manage_sellers=seller.can_manage_sellers,
        db=db,
    )

    await db.commit()
    return await cruds_myeclpay.get_seller(
        user_id=seller.user_id,
        store_id=store_id,
        db=db,
    )


@module.router.get(
    "/myeclpay/stores/{store_id}/sellers",
    status_code=200,
    response_model=list[schemas_myeclpay.Seller],
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
    store = await cruds_myeclpay.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    seller_admin = await cruds_myeclpay.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller_admin is None or not seller_admin.can_manage_sellers:
        raise HTTPException(
            status_code=403,
            detail="User does not have the permission to manage sellers",
        )

    sellers = await cruds_myeclpay.get_sellers_by_store_id(
        store_id=store_id,
        db=db,
    )

    return sellers


@module.router.patch(
    "/myeclpay/stores/{store_id}/sellers/{seller_user_id}",
    status_code=204,
)
async def update_store_seller(
    store_id: UUID,
    seller_user_id: str,
    seller_update: schemas_myeclpay.SellerUpdate,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Update a store seller.

    **The user must have the `can_manage_sellers` permission for this store**
    """
    store = await cruds_myeclpay.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    structure = await cruds_myeclpay.get_structure_by_id(
        structure_id=store.structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )

    if structure.manager_user_id == seller_user_id:
        raise HTTPException(
            status_code=403,
            detail="User is the manager for this structure and cannot be updated as a seller",
        )

    seller_admin = await cruds_myeclpay.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller_admin is None or not seller_admin.can_manage_sellers:
        raise HTTPException(
            status_code=403,
            detail="User does not have the permission to manage sellers",
        )

    seller = await cruds_myeclpay.get_seller(
        user_id=seller_user_id,
        store_id=store_id,
        db=db,
    )

    if seller is None:
        raise HTTPException(
            status_code=404,
            detail="Seller does not exist",
        )

    await cruds_myeclpay.update_seller(
        seller_user_id=seller_user_id,
        store_id=store_id,
        can_bank=seller_update.can_bank or seller.can_bank,
        can_see_history=seller_update.can_see_history or seller.can_see_history,
        can_cancel=seller_update.can_cancel or seller.can_cancel,
        can_manage_sellers=seller_update.can_manage_sellers
        or seller.can_manage_sellers,
        db=db,
    )

    await db.commit()


@module.router.delete(
    "/myeclpay/stores/{store_id}/sellers/{seller_user_id}",
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

    **The user must have the `can_manage_sellers` permission for this store**
    """
    store = await cruds_myeclpay.get_store(
        store_id=store_id,
        db=db,
    )
    if store is None:
        raise HTTPException(
            status_code=404,
            detail="Store does not exist",
        )

    structure = await cruds_myeclpay.get_structure_by_id(
        structure_id=store.structure_id,
        db=db,
    )
    if structure is None:
        raise HTTPException(
            status_code=404,
            detail="Structure does not exist",
        )
    if structure.manager_user_id == seller_user_id:
        raise HTTPException(
            status_code=403,
            detail="User is the manager for this structure and cannot be deleted as a seller",
        )

    seller_admin = await cruds_myeclpay.get_seller(
        user_id=user.id,
        store_id=store_id,
        db=db,
    )
    if seller_admin is None or not seller_admin.can_manage_sellers:
        raise HTTPException(
            status_code=403,
            detail="User does not have the permission to manage sellers",
        )

    seller = await cruds_myeclpay.get_seller(
        user_id=seller_user_id,
        store_id=store_id,
        db=db,
    )

    if seller is None:
        raise HTTPException(
            status_code=404,
            detail="Seller does not exist",
        )

    await cruds_myeclpay.delete_seller(
        seller_user_id=seller_user_id,
        store_id=store_id,
        db=db,
    )

    await db.commit()


@module.router.get(
    "/myeclpay/tos",
    status_code=200,
)
async def get_tos():
    """
    Get the latest TOS version and the TOS content.
    """
    return TOS_CONTENT


@module.router.get(
    "/myeclpay/users/me/tos",
    status_code=200,
    response_model=schemas_myeclpay.TOSSignatureResponse,
)
async def get_user_tos(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Get the latest TOS version and the user signed TOS version.

    **The user must be authenticated to use this endpoint**
    """
    # Check if user is already registered
    existing_user_payment = await cruds_myeclpay.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if existing_user_payment is None:
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    return schemas_myeclpay.TOSSignatureResponse(
        accepted_tos_version=existing_user_payment.accepted_tos_version,
        latest_tos_version=LATEST_TOS,
        tos_content=TOS_CONTENT,
    )


@module.router.post(
    "/myeclpay/users/me/register",
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
    existing_user_payment = await cruds_myeclpay.get_user_payment(
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
    await cruds_myeclpay.create_wallet(
        wallet_id=wallet_id,
        wallet_type=WalletType.USER,
        balance=0,
        db=db,
    )

    await db.commit()

    # Create new payment user with wallet
    await cruds_myeclpay.create_user_payment(
        user_id=user.id,
        wallet_id=wallet_id,
        accepted_tos_signature=datetime.now(UTC),
        accepted_tos_version=0,
        db=db,
    )

    await db.commit()


@module.router.post(
    "/myeclpay/users/me/tos",
    status_code=204,
)
async def sign_tos(
    signature: schemas_myeclpay.TOSSignature,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
):
    """
    Sign MyECL Pay TOS for the given user.

    If the user is already registered in the MyECLPay system, this will update the TOS version.

    **The user must be authenticated to use this endpoint**
    """
    if signature.accepted_tos_version != LATEST_TOS:
        raise HTTPException(
            status_code=400,
            detail=f"Only the latest TOS version {LATEST_TOS} is accepted",
        )

    # Check if user is already registered
    existing_user_payment = await cruds_myeclpay.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if existing_user_payment is None:
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    # Update existing user payment
    await cruds_myeclpay.update_user_payment(
        user_id=user.id,
        accepted_tos_signature=datetime.now(UTC),
        accepted_tos_version=signature.accepted_tos_version,
        db=db,
    )

    await db.commit()

    # TODO: add logs
    # hyperion_security_logger.warning(
    #     f"Create_user: an user with email {user_create.email} already exists ({request_id})",
    # )
    if settings.SMTP_ACTIVE:
        account_exists_content = templates.get_template(
            "myeclpay_signed_tos_mail.html",
        ).render()
        background_tasks.add_task(
            send_email,
            recipient=user.email,
            subject="MyECL - You signed the Terms of Service for MyECLPay",
            content=account_exists_content,
            settings=settings,
        )


@module.router.get(
    "/myeclpay/users/me/wallet/devices",
    status_code=200,
    response_model=list[schemas_myeclpay.WalletDevice],
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
    user_payment = await cruds_myeclpay.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if user_payment is None or not is_user_latest_tos_signed(user_payment):
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    wallet_devices = await cruds_myeclpay.get_wallet_devices_by_wallet_id(
        wallet_id=user_payment.wallet_id,
        db=db,
    )

    return wallet_devices


@module.router.get(
    "/myeclpay/users/me/wallet/devices/{wallet_device_id}",
    status_code=200,
    response_model=schemas_myeclpay.WalletDevice,
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
    user_payment = await cruds_myeclpay.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if user_payment is None or not is_user_latest_tos_signed(user_payment):
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    wallet_devices = await cruds_myeclpay.get_wallet_device(
        wallet_device_id=wallet_device_id,
        db=db,
    )

    if wallet_devices is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet device does not exist",
        )

    if wallet_devices.wallet_id != user_payment.wallet_id:
        raise HTTPException(
            status_code=400,
            detail="Wallet device does not belong to the user",
        )

    return wallet_devices


@module.router.get(
    "/myeclpay/users/me/wallet",
    status_code=200,
    response_model=schemas_myeclpay.Wallet,
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
    user_payment = await cruds_myeclpay.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if user_payment is None or not is_user_latest_tos_signed(user_payment):
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    wallet = await cruds_myeclpay.get_wallet(
        wallet_id=user_payment.wallet_id,
        db=db,
    )

    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet does not exist",
        )

    return wallet


@module.router.post(
    "/myeclpay/users/me/wallet/devices",
    status_code=201,
    response_model=schemas_myeclpay.WalletDevice,
)
async def create_user_devices(
    wallet_device_creation: schemas_myeclpay.WalletDeviceCreation,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
):
    """
    Create a new device for the user.
    The user will need to activate it using a token sent by email.

    **The user must be authenticated to use this endpoint**
    """
    # Check if user is already registered
    user_payment = await cruds_myeclpay.get_user_payment(
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
        ed25519_public_key=wallet_device_creation.ed25519_public_key,
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.INACTIVE,
        activation_token=activation_token,
    )

    await cruds_myeclpay.create_wallet_device(
        wallet_device=wallet_device_db,
        db=db,
    )

    await db.commit()

    if settings.SMTP_ACTIVE:
        account_exists_content = templates.get_template(
            "activate_myeclpay_device_mail.html",
        ).render(
            {
                "activation_link": f"{settings.CLIENT_URL}myeclpay/devices/activate?token={activation_token}",
            },
        )
        background_tasks.add_task(
            send_email,
            recipient=user.email,
            subject="MyECL - activate your device",
            content=account_exists_content,
            settings=settings,
        )
    else:
        hyperion_error_logger.warning(
            f"MyECLPay: activate your device using the token: {activation_token}",
        )

    return wallet_device_db


@module.router.get(
    "/myeclpay/devices/activate",
    status_code=200,
)
async def activate_user_device(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Activate a wallet device
    """

    wallet_device = await cruds_myeclpay.get_wallet_device_by_activation_token(
        activation_token=token,
        db=db,
    )

    if wallet_device is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid token",
        )

    if wallet_device.status != WalletDeviceStatus.INACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Wallet device is already activated or revoked",
        )

    await cruds_myeclpay.update_wallet_device_status(
        wallet_device_id=wallet_device.id,
        status=WalletDeviceStatus.ACTIVE,
        db=db,
    )

    await db.commit()

    wallet = await cruds_myeclpay.get_wallet(
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
            f"Wallet device {wallet_device.id} activated by user {user.id}",
        )

    return "Wallet device activated"


@module.router.post(
    "/myeclpay/users/me/wallet/devices/{wallet_device_id}/revoke",
    status_code=204,
)
async def revoke_user_devices(
    wallet_device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
):
    """
    Revoke a device for the user.

    **The user must be authenticated to use this endpoint**
    """
    # Check if user is already registered
    user_payment = await cruds_myeclpay.get_user_payment(
        user_id=user.id,
        db=db,
    )
    if user_payment is None or not is_user_latest_tos_signed(user_payment):
        raise HTTPException(
            status_code=400,
            detail="User is not registered for MyECL Pay",
        )

    wallet_device = await cruds_myeclpay.get_wallet_device(
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

    await cruds_myeclpay.update_wallet_device_status(
        wallet_device_id=wallet_device_id,
        status=WalletDeviceStatus.REVOKED,
        db=db,
    )

    await db.commit()


@module.router.get(
    "/myeclpay/users/me/wallet/history",
    response_model=list[schemas_myeclpay.History],
)
async def get_user_wallet_history(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
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

    is_user_latest_tos_signed(user_payment)

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


@module.router.post(
    "/myeclpay/transfer/",
    response_model=schemas_payment.PaymentUrl,
    status_code=201,
)
async def get_payment_url(
    transfer_info: schemas_myeclpay.TransferInfo,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
    payment_tool: PaymentTool = Depends(get_payment_tool),
):
    """
    Get payment url
    """
    if transfer_info.amount < 100:
        raise HTTPException(
            status_code=403,
            detail="Please give an amount in cents, greater than 1€.",
        )

    if transfer_info.transfer_type is not TransferType.HELLO_ASSO:
        if transfer_info.receiver_user_id is None:
            raise HTTPException(
                status_code=403,
                detail="Please provide a receiver user id for this transfer type",
            )
        if GroupType.BDE not in [group.id for group in user.groups]:
            raise HTTPException(
                status_code=403,
                detail="User is not allowed to approve this transfer",
            )
        receiver_user = await cruds_users.get_user_by_id(
            user_id=transfer_info.receiver_user_id,
            db=db,
        )
        if receiver_user is None:
            raise HTTPException(
                status_code=404,
                detail="Receiver user does not exist",
            )
    else:
        receiver_user = user

    user_payment = await cruds_myeclpay.get_user_payment(
        user_id=receiver_user.id,
        db=db,
    )
    if user_payment is None:
        raise HTTPException(
            status_code=404,
            detail="User is not registered for MyECL Pay",
        )

    wallet = await cruds_myeclpay.get_wallet(
        wallet_id=user_payment.wallet_id,
        db=db,
    )
    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet does not exist",
        )
    if wallet.balance + transfer_info.amount > settings.MYECLPAY_MAXIMUM_WALLET_BALANCE:
        raise HTTPException(
            status_code=403,
            detail="Wallet balance would exceed the maximum allowed balance",
        )

    if transfer_info.transfer_type is TransferType.HELLO_ASSO:
        user_schema = schemas_core.CoreUser(
            account_type=receiver_user.account_type,
            school_id=receiver_user.school_id,
            email=receiver_user.email,
            birthday=receiver_user.birthday,
            promo=receiver_user.promo,
            floor=receiver_user.floor,
            phone=receiver_user.phone,
            created_on=receiver_user.created_on,
            groups=[],
            id=receiver_user.id,
            name=receiver_user.name,
            firstname=receiver_user.firstname,
            nickname=receiver_user.nickname,
        )
        checkout = await payment_tool.init_checkout(
            module="myeclpay",
            helloasso_slug="AEECL",
            checkout_amount=transfer_info.amount,
            checkout_name="Recharge MyECL Pay",
            redirection_uri=settings.MYECLPAY_PAYMENT_REDIRECTION_URL or "",
            payer_user=user_schema,
            db=db,
        )
        await cruds_myeclpay.create_transfer(
            db=db,
            transfer=schemas_myeclpay.Transfer(
                id=uuid.uuid4(),
                type=transfer_info.transfer_type,
                approver_user_id=None,
                total=transfer_info.amount,
                transfer_identifier=str(checkout.id),
                wallet_id=user_payment.wallet_id,
                creation=datetime.now(UTC),
                confirmed=False,
            ),
        )
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return schemas_payment.PaymentUrl(
            url=checkout.payment_url,
        )
    else:
        await cruds_myeclpay.create_transfer(
            db=db,
            transfer=schemas_myeclpay.Transfer(
                id=uuid.uuid4(),
                type=transfer_info.transfer_type,
                approver_user_id=user.id,
                total=transfer_info.amount,
                transfer_identifier="",
                wallet_id=user_payment.wallet_id,
                creation=datetime.now(UTC),
                confirmed=True,
            ),
        )
        await cruds_myeclpay.increment_wallet_balance(
            wallet_id=user_payment.wallet_id,
            amount=transfer_info.amount,
            db=db,
        )
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        return schemas_payment.PaymentUrl(
            url="",
        )


@module.router.post(
    "/myeclpay/store/{store_id}/scan",
    status_code=204,
)
async def store_scan_qrcode(
    store_id: UUID,
    qr_code_content: schemas_myeclpay.QRCodeContent,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
    request_id: str = Depends(get_request_id),
    notification_tool: NotificationTool = Depends(get_notification_tool),
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
        - the QR Code is intended to be scanned for a store `qr_code_content.store`
        - the signature is valid and correspond to `walled_device_id` public key
        - the giver's wallet device is active
        - the giver's Wallet balance greater than the QR Code total

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

    seller = await cruds_myeclpay.get_seller(
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

    if debited_wallet_device.status != WalletDeviceStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Wallet device is not active",
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

    if not qr_code_content.store:
        raise HTTPException(
            status_code=400,
            detail="QR Code is not intended to be scanned for a store",
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
    if debited_wallet.user is None or debited_wallet.store is not None:
        raise HTTPException(
            status_code=400,
            detail="Stores are not allowed to make transaction by QR code",
        )

    debited_user_payment = await cruds_myeclpay.get_user_payment(
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
    # TODO: rename giver by debited
    await cruds_myeclpay.create_transaction(
        transaction_id=uuid.uuid4(),
        giver_wallet_id=debited_wallet_device.wallet_id,
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

    await db.commit()

    # TODO: log the transaction

    message = Message(
        # context=f"payment-{qr_code_content.qr_code_id}",
        # is_visible=True,
        title=f"💳 Paiement - {store.name}",
        # TODO: convert and add unit
        content=f"Une transaction de {qr_code_content.total} a été effectuée",
        # expire_on=datetime.now(UTC) + timedelta(days=3),
        action_module="MyECLPay",
    )
    await notification_tool.send_notification_to_user(
        user_id=debited_wallet.user.id,
        message=message,
    )

    # TODO: check is the device is revoked or inactive


@module.router.get(
    "/myeclpay/integrity-check",
    status_code=200,
    response_model=tuple[
        list[schemas_myeclpay.Wallet],
        list[schemas_myeclpay.Transaction],
        list[schemas_payment.CheckoutComplete],
    ],
)
async def get_data_for_integrity_check(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Check the integrity of the MyECL Pay database.

    **The header must contain the MYECLPAY_DATA_VERIFIER_ACCESS_TOKEN defined in the settings in the `X-Data-Verifier-Token` header**
    """

    if (
        request.headers.get("X-Data-Verifier-Token")
        != settings.MYECLPAY_DATA_VERIFIER_ACCESS_TOKEN
    ):
        hyperion_security_logger.warning(
            f"A request to /myeclpay/integrity-check has been made with an invalid token, request_content: {request}",
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    wallets = await cruds_myeclpay.get_wallets(
        db=db,
    )
    history = await cruds_myeclpay.get_transactions(
        db=db,
    )
    checkouts = await cruds_payment.get_checkouts(
        module="MyECLPay",
        db=db,
    )

    return wallets, history, checkouts
