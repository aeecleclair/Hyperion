import logging
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import Settings
from app.core.core_endpoints import schemas_core
from app.core.core_endpoints.models_core import CoreUser
from app.core.groups.groups_type import GroupType
from app.core.memberships import cruds_memberships, schemas_memberships
from app.core.myeclpay import cruds_myeclpay, schemas_myeclpay
from app.core.myeclpay.models_myeclpay import Store, WalletDevice
from app.core.myeclpay.types_myeclpay import (
    HistoryType,
    TransactionStatus,
    TransactionType,
    TransferType,
    UnexpectedError,
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
    validate_transfer_callback,
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
from app.types.exceptions import MissingHelloAssoSlugError
from app.types.module import CoreModule
from app.utils.communication.notifications import NotificationTool
from app.utils.mail.mailworker import send_email

router = APIRouter(tags=["Groups"])

core_module = CoreModule(
    root="myeclpay",
    tag="MyECLPay",
    router=router,
    payment_callback=validate_transfer_callback,
)

templates = Jinja2Templates(directory="assets/templates")


hyperion_error_logger = logging.getLogger("hyperion.error")
hyperion_security_logger = logging.getLogger("hyperion.security")


@router.get(
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


@router.post(
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
        association_membership_id=structure.association_membership_id,
        association_membership=None,
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


@router.patch(
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


@router.delete(
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


@router.post(
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


@router.get(
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


@router.post(
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


@router.get(
    "/myeclpay/stores/{store_id}/history",
    status_code=200,
    response_model=list[schemas_myeclpay.History],
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
    history = []
    for transaction in transactions:
        if transaction.debited_wallet_id == store.wallet_id:
            history.append(
                schemas_myeclpay.History(
                    id=transaction.id,
                    type=HistoryType.GIVEN,
                    total=transaction.total,
                    status=transaction.status,
                    creation=transaction.creation,
                    other_wallet_name=transaction.credited_wallet.user.full_name
                    if transaction.credited_wallet.user is not None
                    else "",
                ),
            )
        else:
            history.append(
                schemas_myeclpay.History(
                    id=transaction.id,
                    type=HistoryType.RECEIVED,
                    total=transaction.total,
                    status=transaction.status,
                    creation=transaction.creation,
                    other_wallet_name=transaction.debited_wallet.user.full_name
                    if transaction.debited_wallet.user is not None
                    else "",
                ),
            )

    # TODO: even if this is forbidden, we should return transfer

    return history


@router.get(
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
                        association_membership_id=store.structure.association_membership_id,
                        association_membership=schemas_memberships.MembershipSimple(
                            id=store.structure.association_membership.id,
                            name=store.structure.association_membership.name,
                            group_id=store.structure.association_membership.group_id,
                        )
                        if store.structure.association_membership is not None
                        else None,
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


@router.patch(
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


@router.delete(
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


@router.post(
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


@router.get(
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


@router.patch(
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


@router.delete(
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


@router.get(
    "/myeclpay/tos",
    status_code=200,
)
async def get_tos():
    """
    Get the latest TOS version and the TOS content.
    """
    return TOS_CONTENT


@router.get(
    "/myeclpay/users/me/tos",
    status_code=200,
    response_model=schemas_myeclpay.TOSSignatureResponse,
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
        max_transaction_total=MAX_TRANSACTION_TOTAL,
        max_wallet_balance=settings.MYECLPAY_MAXIMUM_WALLET_BALANCE,
    )


@router.post(
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


@router.post(
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


@router.get(
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


@router.get(
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


@router.get(
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


@router.post(
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


@router.get(
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


@router.post(
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


@router.get(
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

    history: list[schemas_myeclpay.History] = []

    # First we get all received and send transactions
    transactions = await cruds_myeclpay.get_transactions_by_wallet_id(
        wallet_id=user_payment.wallet_id,
        db=db,
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

    for transfer in transfers:
        if transfer.confirmed:
            status = TransactionStatus.CONFIRMED
        elif datetime.now(UTC) < transfer.creation + timedelta(minutes=15):
            status = TransactionStatus.PENDING
        else:
            status = TransactionStatus.CANCELED

        history.append(
            schemas_myeclpay.History(
                id=transfer.id,
                type=HistoryType.TRANSFER,
                other_wallet_name="Transfer",
                total=transfer.total,
                creation=transfer.creation,
                status=status,
            ),
        )

    # We add refunds
    refunds = await cruds_myeclpay.get_refunds_by_wallet_id(
        wallet_id=user_payment.wallet_id,
        db=db,
    )
    for refund in refunds:
        if refund.debited_wallet_id == user_payment.wallet_id:
            transaction_type = HistoryType.GIVEN
            other_wallet_info = refund.credited_wallet
        else:
            transaction_type = HistoryType.RECEIVED
            other_wallet_info = refund.debited_wallet

        history.append(
            schemas_myeclpay.History(
                id=refund.id,
                type=transaction_type,
                other_wallet_name=other_wallet_info.owner_name or "Unknown",
                total=refund.total,
                creation=refund.creation,
                status=TransactionStatus.CONFIRMED,
            ),
        )

    return history
    # TODO: limite by datetime


@router.post(
    "/myeclpay/transfer/admin",
    response_model=None,
    status_code=204,
)
async def add_transfer_by_admin(
    transfer_info: schemas_myeclpay.AdminTransferInfo,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
    payment_tool: PaymentTool = Depends(get_payment_tool),
):
    if transfer_info.transfer_type == TransferType.HELLO_ASSO:
        raise HTTPException(
            status_code=400,
            detail="Admin cannot create a HelloAsso transfer",
        )

    if transfer_info.amount < 100:
        raise HTTPException(
            status_code=400,
            detail="Please give an amount in cents, greater than 1€.",
        )

    if transfer_info.credited_user_id is None:
        raise HTTPException(
            status_code=400,
            detail="Please provide a credited user id for this transfer type",
        )
    # TODO: do not let all BDE do this
    if GroupType.BDE not in [group.id for group in user.groups]:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to approve this transfer",
        )
    credited_user = await cruds_users.get_user_by_id(
        user_id=transfer_info.credited_user_id,
        db=db,
    )
    if credited_user is None:
        raise HTTPException(
            status_code=404,
            detail="Receiver user does not exist",
        )

    user_payment = await cruds_myeclpay.get_user_payment(
        user_id=credited_user.id,
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

    await cruds_myeclpay.create_transfer(
        db=db,
        transfer=schemas_myeclpay.Transfer(
            id=uuid.uuid4(),
            type=transfer_info.transfer_type,
            approver_user_id=user.id,
            total=transfer_info.amount,
            transfer_identifier="",  # TODO: require to provide an identifier
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


@router.post(
    "/myeclpay/transfer/init",
    response_model=schemas_payment.PaymentUrl,
    status_code=201,
)
async def init_ha_transfer(
    transfer_info: schemas_myeclpay.TransferInfo,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user()),
    settings: Settings = Depends(get_settings),
    payment_tool: PaymentTool = Depends(get_payment_tool),
):
    """
    Get payment url
    """
    if settings.HELLOASSO_MYECLPAY_SLUG is None:
        raise MissingHelloAssoSlugError("HELLOASSO_MYECLPAY_SLUG")

    # TODO
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

    user_payment = await cruds_myeclpay.get_user_payment(
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

    user_schema = schemas_core.CoreUser(
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
        module="myeclpay",
        helloasso_slug=settings.HELLOASSO_MYECLPAY_SLUG,
        checkout_amount=transfer_info.amount,
        checkout_name="Recharge MyECL Pay",
        redirection_uri=str(transfer_info.redirect_url),
        payer_user=user_schema,
        db=db,
    )
    await cruds_myeclpay.create_transfer(
        db=db,
        transfer=schemas_myeclpay.Transfer(
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
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return schemas_payment.PaymentUrl(
        url=checkout.payment_url,
    )


@router.post(
    "/myeclpay/stores/{store_id}/scan",
    status_code=201,
    response_model=schemas_myeclpay.Transaction,
)
async def store_scan_qrcode(
    store_id: UUID,
    scan_info: schemas_myeclpay.ScanInfo,
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
        - the QR Code is intended to be scanned for a store `scan_info.store`
        - the signature is valid and correspond to `wallet_device_id` public key
        - the debited's wallet device is active
        - the debited's Wallet balance greater than the QR Code total

    **The user must be authenticated to use this endpoint**
    **The user must have the `can_bank` permission for this store**
    """
    # If the QR Code is already used, we return an error
    already_existing_used_qrcode = await cruds_myeclpay.get_used_qrcode(
        qr_code_id=scan_info.qr_code_id,
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
        qr_code_id=scan_info.qr_code_id,
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
        wallet_device_id=scan_info.wallet_device_id,
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
        data=compute_signable_data(scan_info),
        wallet_device_id=scan_info.wallet_device_id,
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
    if scan_info.total <= 0:
        raise HTTPException(
            status_code=400,
            detail="Total must be greater than 0",
        )

    if scan_info.total > MAX_TRANSACTION_TOTAL:
        raise HTTPException(
            status_code=400,
            detail=f"Total can not exceed {MAX_TRANSACTION_TOTAL}",
        )

    if scan_info.creation < datetime.now(UTC) - timedelta(
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

    if debited_wallet.balance < scan_info.total:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance in the debited wallet",
        )

    if not scan_info.bypass_membership:
        if store.structure.association_membership_id is not None:
            memberships = await cruds_memberships.get_user_memberships_by_user_id_and_association_membership_id(
                user_id=debited_wallet.user.id,
                association_membership_id=store.structure.association_membership_id,
                db=db,
            )
            today = datetime.now(UTC).date()
            if not any(
                membership.start_date <= today <= membership.end_date
                for membership in memberships
            ):
                # We remove the QR Code from the list of used QR Code since we want to allow the seller to scan it again whith a bypass_membership flag if the transaction must be done without a membership
                await cruds_myeclpay.delete_used_qrcode(
                    qr_code_id=scan_info.qr_code_id,
                    db=db,
                )
                raise HTTPException(
                    status_code=400,
                    detail="User does not have the required membership",
                )

    # We increment the receiving wallet balance
    await cruds_myeclpay.increment_wallet_balance(
        wallet_id=store.wallet_id,
        amount=scan_info.total,
        db=db,
    )

    # We decrement the debited wallet balance
    await cruds_myeclpay.increment_wallet_balance(
        wallet_id=debited_wallet.id,
        amount=-scan_info.total,
        db=db,
    )
    transaction_id = uuid.uuid4()
    # We create a transaction
    await cruds_myeclpay.create_transaction(
        transaction_id=transaction_id,
        debited_wallet_id=debited_wallet_device.wallet_id,
        debited_wallet_device_id=debited_wallet_device.id,
        credited_wallet_id=store.wallet_id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=user.id,
        total=scan_info.total,
        creation=datetime.now(UTC),
        status=TransactionStatus.CONFIRMED,
        store_note=None,
        db=db,
    )

    await db.commit()

    # TODO: log the transaction

    message = Message(
        # context=f"payment-{scan_info.qr_code_id}",
        # is_visible=True,
        title=f"💳 Paiement - {store.name}",
        # TODO: convert and add unit
        content=f"Une transaction de {scan_info.total/100} € a été effectuée",
        # expire_on=datetime.now(UTC) + timedelta(days=3),
        action_module="MyECLPay",
    )
    await notification_tool.send_notification_to_user(
        user_id=debited_wallet.user.id,
        message=message,
    )

    # TODO: check is the device is revoked or inactive

    return schemas_myeclpay.Transaction(
        id=transaction_id,
        debited_wallet_id=debited_wallet_device.wallet_id,
        credited_wallet_id=store.wallet_id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=user.id,
        total=scan_info.total,
        creation=datetime.now(UTC),
        status=TransactionStatus.CONFIRMED,
    )


@router.post(
    "/myeclpay/transactions/{transaction_id}/refund",
    status_code=204,
)
async def refund_transaction(
    transaction_id: UUID,
    refund_info: schemas_myeclpay.RefundInfo,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
    request_id: str = Depends(get_request_id),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Refund a transaction

    **The user must either be the credited user or a seller with cancel permissions of the credited store of the transaction**
    """
    transaction = await cruds_myeclpay.get_transaction(
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
    wallet_previously_credited = await cruds_myeclpay.get_wallet(
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
        seller = await cruds_myeclpay.get_seller(
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
        if refund_info.amount >= transaction.total:
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
    wallet_previously_debited = await cruds_myeclpay.get_wallet(
        wallet_id=transaction.debited_wallet_id,
        db=db,
    )
    if wallet_previously_debited is None:
        raise HTTPException(
            status_code=404,
            detail="The wallet that should be credited during the refund does not exist",
        )

    await cruds_myeclpay.update_transaction_status(
        transaction_id=transaction_id,
        status=TransactionStatus.REFUNDED,
        db=db,
    )

    await cruds_myeclpay.create_refund(
        refund=schemas_myeclpay.RefundBase(
            id=uuid.uuid4(),
            transaction_id=transaction_id,
            total=refund_amount,
            seller_user_id=user.id
            if wallet_previously_credited.type == WalletType.STORE
            else None,
            credited_wallet_id=wallet_previously_debited.id,
            debited_wallet_id=wallet_previously_credited.id,
            creation=datetime.now(UTC),
        ),
        db=db,
    )

    # We add the amount to the wallet that was previously debited
    await cruds_myeclpay.increment_wallet_balance(
        wallet_id=wallet_previously_debited.id,
        amount=refund_amount,
        db=db,
    )

    await cruds_myeclpay.increment_wallet_balance(
        wallet_id=wallet_previously_credited.id,
        amount=-refund_amount,
        db=db,
    )

    await db.commit()

    if wallet_previously_debited.user is not None:
        message = Message(
            title="💳 Remboursement",
            content=f"La transaction pour {wallet_previously_credited_name} ({transaction.total/100} €) a été remboursée de {refund_amount/100} €",
            action_module="MyECLPay",
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
            content=f"Vous avez remboursé la transaction de {wallet_previously_debited_name} ({transaction.total/100} €) de {refund_amount/100} €",
            action_module="MyECLPay",
        )
        await notification_tool.send_notification_to_user(
            user_id=wallet_previously_credited.user.id,
            message=message,
        )


@router.post(
    "/myeclpay/transactions/{transaction_id}/cancel",
    status_code=204,
)
async def cancel_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
    request_id: str = Depends(get_request_id),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    """
    Cancel a transaction

    **The user must either be the credited user or the seller of the transaction**
    """
    transaction = await cruds_myeclpay.get_transaction(
        transaction_id=transaction_id,
        db=db,
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction does not exist",
        )

    canceller_wallet = await cruds_myeclpay.get_wallet(
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
        seller = await cruds_myeclpay.get_seller(
            store_id=canceller_wallet.store.id,
            user_id=user.id,
            db=db,
        )
        if seller is None:
            raise HTTPException(
                status_code=403,
                detail="User does not have the permission to cancel this transaction",
            )
        if datetime.now(UTC) - transaction.creation > timedelta(seconds=30):
            if not seller.can_cancel:
                raise HTTPException(
                    status_code=403,
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

    if transaction.status == TransactionStatus.CANCELED:
        raise HTTPException(
            status_code=400,
            detail="Transaction is already canceled",
        )

    debited_wallet = await cruds_myeclpay.get_wallet(
        wallet_id=transaction.debited_wallet_id,
        db=db,
    )
    if debited_wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Debited wallet does not exist",
        )

    await cruds_myeclpay.update_transaction_status(
        transaction_id=transaction_id,
        status=TransactionStatus.CANCELED,
        db=db,
    )

    await cruds_myeclpay.increment_wallet_balance(
        wallet_id=transaction.debited_wallet_id,
        amount=transaction.total,
        db=db,
    )

    await cruds_myeclpay.increment_wallet_balance(
        wallet_id=transaction.credited_wallet_id,
        amount=-transaction.total,
        db=db,
    )

    await db.commit()
    if debited_wallet.user is not None:
        message = Message(
            title="💳 Paiement annulé",
            content=f"La transaction de {transaction.total/100} € a été annulée",
            action_module="MyECLPay",
        )
        await notification_tool.send_notification_to_user(
            user_id=debited_wallet.user.id,
            message=message,
        )


@router.get(
    "/myeclpay/integrity-check",
    status_code=200,
    response_model=tuple[
        list[schemas_myeclpay.Wallet],
        list[schemas_myeclpay.Transaction],
        list[schemas_payment.CheckoutComplete],
        list[schemas_myeclpay.Transfer],
        list[schemas_myeclpay.Refund],
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
    transactions = await cruds_myeclpay.get_transactions(
        db=db,
    )
    checkouts = await cruds_payment.get_checkouts(
        module="MyECLPay",
        db=db,
    )
    transfers = await cruds_myeclpay.get_transfers(
        db=db,
    )
    refunds = await cruds_myeclpay.get_refunds(
        db=db,
    )

    return wallets, transactions, checkouts, transfers, refunds
