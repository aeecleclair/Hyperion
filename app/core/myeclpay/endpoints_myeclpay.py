import logging
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import Settings
from app.core.groups.groups_type import GroupType
from app.core.models_core import CoreUser
from app.core.myeclpay import cruds_myeclpay, schemas_myeclpay
from app.core.myeclpay.models_myeclpay import Store, WalletDevice
from app.core.myeclpay.types_myeclpay import (
    HistoryType,
    TransactionStatus,
    TransactionType,
    WalletDeviceStatus,
    WalletType,
)
from app.core.myeclpay.utils_myeclpay import (
    CGU_CONTENT,
    LATEST_CGU,
    MAX_TRANSACTION_TOTAL,
    QRCODE_EXPIRATION,
    compute_signable_data,
    is_user_latest_cgu_signed,
    verify_signature,
)
from app.core.notification.schemas_notification import Message
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_request_id,
    get_settings,
    is_user_a_member_of,
    is_user_an_ecl_member,
)
from app.utils.communication.notifications import NotificationTool
from app.utils.mail.mailworker import send_email
from app.utils.tools import get_display_name

router = APIRouter(tags=["MyECLPay"])

templates = Jinja2Templates(directory="assets/templates")


hyperion_error_logger = logging.getLogger("hyperion.error")


# Members of group Payment #


@router.post(
    "/myeclpay/stores",
    status_code=200,
    response_model=schemas_myeclpay.Store,
)
async def create_store(
    store: schemas_myeclpay.StoreBase,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_a_member_of(GroupType.payment)),
):
    """
    Create a store

    **The user must be a member of group Payment**
    """
    # Create new wallet for user
    wallet_id = uuid.uuid4()
    await cruds_myeclpay.create_wallet(
        wallet_id=wallet_id,
        wallet_type=WalletType.USER,
        balance=0,
        db=db,
    )

    store_db = Store(
        id=uuid.uuid4(),
        name=store.name,
        membership=store.membership,
        wallet_id=wallet_id,
    )
    # Check if user is already registered
    await cruds_myeclpay.create_store(
        store=store_db,
        db=db,
    )

    await db.commit()

    return store_db


@router.post(
    "/myeclpay/stores/{store_id}/admins",
    status_code=204,
)
async def create_store_admin_seller(
    store_id: UUID,
    seller: schemas_myeclpay.SellerAdminCreation,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_a_member_of(GroupType.payment)),
):
    """
    Create a store admin seller.

    This admin will have permissions:
    - can_bank
    - can_see_history
    - can_cancel
    - can_manage_sellers
    - store_admin

    **The user must be a member of group Payment**
    """
    await cruds_myeclpay.create_seller(
        user_id=seller.user_id,
        store_id=store_id,
        can_bank=True,
        can_see_history=True,
        can_cancel=True,
        can_manage_sellers=True,
        store_admin=True,
        db=db,
    )

    await db.commit()


@router.get(
    "/myeclpay/stores/{store_id}/admins",
    status_code=200,
    response_model=list[schemas_myeclpay.Seller],
)
async def get_store_admin_seller(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_a_member_of(GroupType.payment)),
):
    """
    Get all sellers that have the `store_admin` permission for the given store.

    **The user must be a member of group Payment**
    """
    sellers = await cruds_myeclpay.get_admin_sellers(
        store_id=store_id,
        db=db,
    )

    return sellers


@router.delete(
    "/myeclpay/stores/{store_id}/admins/{seller_user_id}",
    status_code=204,
)
async def delete_store_admin_seller(
    store_id: UUID,
    seller_user_id: str,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_a_member_of(GroupType.payment)),
):
    """
    Delete a store admin seller.

    **The user must be a member of group Payment**
    """
    seller = await cruds_myeclpay.get_seller(
        seller_user_id=seller_user_id,
        store_id=store_id,
        db=db,
    )

    if seller is None:
        raise HTTPException(
            status_code=404,
            detail="Seller does not exist",
        )

    if not seller.store_admin:
        raise HTTPException(
            status_code=400,
            detail="Seller is not a store admin",
        )

    await cruds_myeclpay.delete_seller(
        seller_user_id=seller_user_id,
        store_id=store_id,
        db=db,
    )

    await db.commit()


# Store admin #


@router.patch(
    "/myeclpay/stores/{store_id}",
    status_code=204,
)
async def update_store(
    store_id: UUID,
    store_update: schemas_myeclpay.StoreUpdate,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Update a store

    **The user must be a member of group Payment**
    """
    seller = await cruds_myeclpay.get_seller(
        seller_user_id=user.id,
        store_id=store_id,
        db=db,
    )

    if seller is None or not seller.store_admin:
        raise HTTPException(
            status_code=403,
            detail="User is not a store admin seller for this store",
        )

    await cruds_myeclpay.update_store(
        store_id=store_id,
        store_update=store_update,
        db=db,
    )

    await db.commit()


# User registration #


@router.get(
    "/myeclpay/users/me/cgu",
    status_code=200,
    response_model=schemas_myeclpay.CGUSignatureResponse,
)
async def get_cgu(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Get the latest CGU version and the user signed CGU version.

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

    return schemas_myeclpay.CGUSignatureResponse(
        accepted_cgu_version=existing_user_payment.accepted_cgu_version,
        latest_cgu_version=LATEST_CGU,
        cgu_content=CGU_CONTENT,
    )


@router.post(
    "/myeclpay/users/me/register",
    status_code=204,
)
async def register_user(
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Sign MyECL Pay CGU for the given user.

    The user will need to accept the latest CGU version to be able to use MyECL Pay.

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
        accepted_cgu_signature=datetime.now(UTC),
        accepted_cgu_version=0,
        db=db,
    )

    await db.commit()


@router.post(
    "/myeclpay/users/me/cgu",
    status_code=204,
)
async def sign_cgu(
    signature: schemas_myeclpay.CGUSignature,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
    settings: Settings = Depends(get_settings),
):
    """
    Sign MyECL Pay CGU for the given user.

    If the user is already registered in the MyECLPay system, this will update the CGU version.

    **The user must be authenticated to use this endpoint**
    """
    if signature.accepted_cgu_version != LATEST_CGU:
        raise HTTPException(
            status_code=400,
            detail=f"Only the latest CGU version {LATEST_CGU} is accepted",
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
        accepted_cgu_signature=datetime.now(UTC),
        accepted_cgu_version=signature.accepted_cgu_version,
        db=db,
    )

    await db.commit()

    # TODO: add logs
    # hyperion_security_logger.warning(
    #     f"Create_user: an user with email {user_create.email} already exists ({request_id})",
    # )
    # TODO: change template
    if settings.SMTP_ACTIVE:
        account_exists_content = templates.get_template(
            "account_exists_mail.html",
        ).render()
        background_tasks.add_task(
            send_email,
            recipient=user.email,
            subject="MyECL - you have signed CGU",
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
    user: CoreUser = Depends(is_user_an_ecl_member),
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
    if user_payment is None or not is_user_latest_cgu_signed(user_payment):
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
    user: CoreUser = Depends(is_user_an_ecl_member),
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
    if user_payment is None or not is_user_latest_cgu_signed(user_payment):
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


@router.post(
    "/myeclpay/users/me/wallet/devices",
    status_code=201,
    response_model=schemas_myeclpay.WalletDevice,
)
async def create_user_devices(
    wallet_device_creation: schemas_myeclpay.WalletDeviceCreation,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
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
    if user_payment is None or not is_user_latest_cgu_signed(user_payment):
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

    # TODO: use the correct template content
    if settings.SMTP_ACTIVE:
        account_exists_content = templates.get_template(
            "account_exists_mail.html",
        ).render()
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
    "/myeclpay/users/me/wallet/devices/activate/{activation_token}",
    status_code=200,
)
async def activate_user_device(
    activation_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Activate a wallet device
    """

    wallet_device = await cruds_myeclpay.get_wallet_device_by_activation_token(
        activation_token=activation_token,
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

    return "Wallet device activated"


@router.post(
    "/myeclpay/users/me/wallet/devices/{wallet_device_id}/revoke",
    status_code=204,
)
async def revoke_user_devices(
    wallet_device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CoreUser = Depends(is_user_an_ecl_member),
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
    if user_payment is None or not is_user_latest_cgu_signed(user_payment):
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
        status=WalletDeviceStatus.DISABLED,
        db=db,
    )


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

    is_user_latest_cgu_signed(user_payment)

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
    if debited_user_payment is None or not is_user_latest_cgu_signed(
        debited_user_payment,
    ):
        raise HTTPException(
            status_code=400,
            detail="Debited user has not signed the latest CGU",
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
        context=f"payment-{qr_code_content.qr_code_id}",
        is_visible=True,
        title=f"💳 Paiement - {store.name}",
        # TODO: convert and add unit
        content=f"Une transaction de {qr_code_content.total} a été effectuée",
        expire_on=datetime.now(UTC) + timedelta(days=3),
    )
    await notification_tool.send_notification_to_user(
        user_id=debited_wallet.user.id,
        message=message,
    )

    # TODO: check is the device is revoked or inactive
