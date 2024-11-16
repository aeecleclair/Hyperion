import base64
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.myeclpay import cruds_myeclpay, models_myeclpay
from app.core.myeclpay.schemas_myeclpay import QRCodeContentBase
from app.core.myeclpay.types_myeclpay import (
    TransactionStatus,
    TransactionType,
    TransferType,
    WalletDeviceStatus,
    WalletType,
)
from app.core.myeclpay.utils_myeclpay import LATEST_CGU, compute_signable_data
from app.types.membership import AvailableAssociationMembership
from tests.commons import (
    TestingSessionLocal,
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

ecl_user: models_core.CoreUser
ecl_user_access_token: str
ecl_user_wallet: models_myeclpay.Wallet
ecl_user_wallet_device_private_key: Ed25519PrivateKey
ecl_user_wallet_device: models_myeclpay.WalletDevice
ecl_user_wallet_device_unactive: models_myeclpay.WalletDevice
ecl_user_payment: models_myeclpay.UserPayment
ecl_user_transfer: models_myeclpay.Transfer

ecl_user2: models_core.CoreUser
ecl_user2_access_token: str
ecl_user2_wallet: models_myeclpay.Wallet
ecl_user2_wallet_device: models_myeclpay.WalletDevice
ecl_user2_payment: models_myeclpay.UserPayment

store_wallet: models_myeclpay.Wallet
store: models_myeclpay.Store
store_wallet_device_private_key: Ed25519PrivateKey
store_wallet_device: models_myeclpay.WalletDevice


transaction_from_ecl_user_to_store: models_myeclpay.Transaction
transaction_from_ecl_user_to_ecl_user2: models_myeclpay.Transaction
transaction_from_store_to_ecl_user: models_myeclpay.Transaction
transaction_from_ecl_user2_to_ecl_user: models_myeclpay.Transaction

used_qr_code: models_myeclpay.UsedQRCode

store_seller_no_permission_user_access_token: str
store_seller_can_bank_user_access_token: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    # ecl_user

    global ecl_user, ecl_user_access_token
    ecl_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    ecl_user_access_token = create_api_access_token(ecl_user)

    global ecl_user_wallet
    ecl_user_wallet = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.USER,
        balance=1000,  # 10€
    )
    await add_object_to_db(ecl_user_wallet)

    global ecl_user_payment
    ecl_user_payment = models_myeclpay.UserPayment(
        user_id=ecl_user.id,
        wallet_id=ecl_user_wallet.id,
        accepted_cgu_signature=datetime.now(UTC),
        accepted_cgu_version=LATEST_CGU,
    )
    await add_object_to_db(ecl_user_payment)

    global \
        ecl_user_wallet_device, \
        ecl_user_wallet_device_private_key, \
        ecl_user_wallet_device_unactive
    ecl_user_wallet_device_private_key = Ed25519PrivateKey.generate()
    ecl_user_wallet_device = models_myeclpay.WalletDevice(
        id=uuid4(),
        name="Test device",
        wallet_id=ecl_user_wallet.id,
        ed25519_public_key=ecl_user_wallet_device_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ),
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.ACTIVE,
        activation_token="activation_token_ecl_user_wallet_device",
    )
    await add_object_to_db(ecl_user_wallet_device)
    ecl_user_wallet_device_unactive = models_myeclpay.WalletDevice(
        id=uuid4(),
        name="Test device unactive",
        wallet_id=ecl_user_wallet.id,
        ed25519_public_key=b"key",
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.UNACTIVE,
        activation_token="activation_token_ecl_user_wallet_device_unactive",
    )
    await add_object_to_db(ecl_user_wallet_device_unactive)

    # ecl_user2
    global ecl_user2, ecl_user2_access_token
    ecl_user2 = await create_user_with_groups(
        firstname="firstname",
        name="ECL User 2",
        nickname="nickname",
        groups=[GroupType.student],
    )
    ecl_user2_access_token = create_api_access_token(ecl_user2)

    global ecl_user2_wallet
    ecl_user2_wallet = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.USER,
        balance=2000,  # 20€
    )
    await add_object_to_db(ecl_user2_wallet)

    global ecl_user2_payment
    ecl_user2_payment = models_myeclpay.UserPayment(
        user_id=ecl_user2.id,
        wallet_id=ecl_user2_wallet.id,
        accepted_cgu_signature=datetime.now(UTC),
        accepted_cgu_version=LATEST_CGU,
    )
    await add_object_to_db(ecl_user2_payment)

    global ecl_user2_wallet_device
    ecl_user2_wallet_device = models_myeclpay.WalletDevice(
        id=uuid4(),
        name="Test device",
        wallet_id=ecl_user2_wallet.id,
        ed25519_public_key=b"ed25519_public_key",
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.ACTIVE,
        activation_token="activation_token_ecl_user2_wallet_device",
    )
    await add_object_to_db(ecl_user2_wallet_device)

    # store
    global store_wallet
    store_wallet = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.STORE,
        balance=5000,  # 50€
    )
    await add_object_to_db(store_wallet)

    global store
    store = models_myeclpay.Store(
        id=uuid4(),
        wallet_id=store_wallet.id,
        name="Test Store",
        membership=AvailableAssociationMembership.aeecl,
    )
    await add_object_to_db(store)

    # NOTE: in practice we won't allow a store to emit transactions and to have a WalletDevice
    global store_wallet_device, store_wallet_device_private_key
    store_wallet_device_private_key = Ed25519PrivateKey.generate()
    store_wallet_device = models_myeclpay.WalletDevice(
        id=uuid4(),
        name="Store test device",
        wallet_id=store_wallet.id,
        ed25519_public_key=store_wallet_device_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ),
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.ACTIVE,
        activation_token="activation_token",
    )
    await add_object_to_db(store_wallet_device)

    # Create test transactions
    global transaction_from_ecl_user_to_store
    transaction_from_ecl_user_to_store = models_myeclpay.Transaction(
        id=uuid4(),
        giver_wallet_id=ecl_user_wallet.id,
        giver_wallet_device_id=ecl_user_wallet_device.id,
        receiver_wallet_id=store_wallet.id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=ecl_user2.id,
        total=500,  # 5€
        creation=datetime.now(UTC),
        status=TransactionStatus.CONFIRMED,
        store_note="transaction_from_ecl_user_to_store",
    )
    await add_object_to_db(transaction_from_ecl_user_to_store)

    global transaction_from_ecl_user_to_ecl_user2
    transaction_from_ecl_user_to_ecl_user2 = models_myeclpay.Transaction(
        id=uuid4(),
        giver_wallet_id=ecl_user_wallet.id,
        giver_wallet_device_id=ecl_user_wallet_device.id,
        receiver_wallet_id=ecl_user2_wallet.id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=ecl_user2.id,
        total=600,
        creation=datetime.now(UTC),
        status=TransactionStatus.CONFIRMED,
        store_note="transaction_from_ecl_user_to_ecl_user2",
    )
    await add_object_to_db(transaction_from_ecl_user_to_ecl_user2)

    global transaction_from_store_to_ecl_user
    transaction_from_store_to_ecl_user = models_myeclpay.Transaction(
        id=uuid4(),
        giver_wallet_id=store_wallet.id,
        giver_wallet_device_id=store_wallet_device.id,
        receiver_wallet_id=ecl_user_wallet.id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=ecl_user2.id,
        total=700,
        creation=datetime.now(UTC),
        status=TransactionStatus.CONFIRMED,
        store_note="transaction_from_store_to_ecl_user",
    )
    await add_object_to_db(transaction_from_store_to_ecl_user)

    global transaction_from_ecl_user2_to_ecl_user
    transaction_from_ecl_user2_to_ecl_user = models_myeclpay.Transaction(
        id=uuid4(),
        giver_wallet_id=ecl_user2_wallet.id,
        giver_wallet_device_id=ecl_user2_wallet_device.id,
        receiver_wallet_id=ecl_user_wallet.id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=ecl_user2.id,
        total=800,
        creation=datetime.now(UTC),
        status=TransactionStatus.CONFIRMED,
        store_note="transaction_from_ecl_user2_to_ecl_user",
    )
    await add_object_to_db(transaction_from_ecl_user2_to_ecl_user)

    # Add a transfer
    global ecl_user_transfer
    ecl_user_transfer = models_myeclpay.Transfer(
        id=uuid4(),
        type=TransferType.HELLO_ASSO,
        transfer_identifier="transfer_identifier",
        approver_user_id=None,
        wallet_id=ecl_user_wallet.id,
        total=1000,  # 10€
        creation=datetime.now(UTC),
    )
    await add_object_to_db(ecl_user_transfer)

    # QR Code
    global used_qr_code
    used_qr_code = models_myeclpay.UsedQRCode(
        qr_code_id=uuid4(),
    )
    await add_object_to_db(used_qr_code)

    # Sellers
    global store_seller_no_permission_user_access_token
    store_seller_no_permission_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    store_seller_no_permission_user_access_token = create_api_access_token(
        store_seller_no_permission_user,
    )
    store_seller_no_permission = models_myeclpay.Seller(
        user_id=store_seller_no_permission_user.id,
        store_id=store.id,
        can_bank=False,
        can_see_historic=False,
        can_cancel=False,
        can_manage_sellers=False,
        store_admin=False,
    )
    await add_object_to_db(store_seller_no_permission)

    global store_seller_can_bank_user_access_token
    store_seller_can_bank_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    store_seller_can_bank_user_access_token = create_api_access_token(
        store_seller_can_bank_user,
    )
    store_seller_can_bank = models_myeclpay.Seller(
        user_id=store_seller_can_bank_user.id,
        store_id=store.id,
        can_bank=True,
        can_see_historic=False,
        can_cancel=False,
        can_manage_sellers=False,
        store_admin=False,
    )
    await add_object_to_db(store_seller_can_bank)


async def get_cgu_for_unregistred_user(client: TestClient):
    unregistred_ecl_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    unregistred_ecl_user_access_token = create_api_access_token(unregistred_ecl_user)

    response = client.get(
        "/myeclpay/users/me/cgu",
        headers={"Authorization": f"Bearer {unregistred_ecl_user_access_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is not registered for MyECL Pa"


async def test_register_new_user(client: TestClient):
    unregistred_ecl_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    unregistred_ecl_user_access_token = create_api_access_token(unregistred_ecl_user)

    response = client.post(
        "/myeclpay/users/me/register",
        headers={"Authorization": f"Bearer {unregistred_ecl_user_access_token}"},
        json={"accepted_cgu_version": 1},
    )
    assert response.status_code == 204

    response = client.post(
        "/myeclpay/users/me/register",
        headers={"Authorization": f"Bearer {unregistred_ecl_user_access_token}"},
        json={"accepted_cgu_version": 1},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is already registered for MyECL Pay"


async def test_sign_cgu_for_old_cgu_version(client: TestClient):
    unregistred_ecl_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    unregistred_ecl_user_access_token = create_api_access_token(unregistred_ecl_user)

    response = client.post(
        "/myeclpay/users/me/cgu",
        headers={"Authorization": f"Bearer {unregistred_ecl_user_access_token}"},
        json={"accepted_cgu_version": 0},
    )
    assert response.status_code == 400
    assert response.json()["detail"][:27] == "Only the latest CGU version"


async def test_sign_cgu_for_unregistred_user(client: TestClient):
    unregistred_ecl_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    unregistred_ecl_user_access_token = create_api_access_token(unregistred_ecl_user)

    response = client.post(
        "/myeclpay/users/me/cgu",
        headers={"Authorization": f"Bearer {unregistred_ecl_user_access_token}"},
        json={"accepted_cgu_version": 1},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


async def test_sign_cgu(client: TestClient):
    unregistred_ecl_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    unregistred_ecl_user_access_token = create_api_access_token(unregistred_ecl_user)

    response = client.post(
        "/myeclpay/users/me/register",
        headers={"Authorization": f"Bearer {unregistred_ecl_user_access_token}"},
        json={"accepted_cgu_version": 2},
    )
    assert response.status_code == 204


async def test_get_transactions_unregistered(client: TestClient):
    unregistred_ecl_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    unregistred_ecl_user_access_token = create_api_access_token(unregistred_ecl_user)

    response = client.get(
        "/myeclpay/users/me/wallet/history",
        headers={"Authorization": f"Bearer {unregistred_ecl_user_access_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


def test_get_transactions_success(client: TestClient):
    """Test successfully getting user transactions"""
    response = client.get(
        "/myeclpay/users/me/wallet/history",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200

    transactions = response.json()
    assert len(transactions) == 5
    transactions_dict = {UUID(t["id"]): t for t in transactions}

    assert (
        transactions_dict[transaction_from_ecl_user_to_store.id]["other_wallet_name"]
        == "Test Store"
    )
    assert transactions_dict[transaction_from_ecl_user_to_store.id]["type"] == "given"
    assert transactions_dict[transaction_from_ecl_user_to_store.id]["total"] == 500
    assert (
        transactions_dict[transaction_from_ecl_user_to_store.id]["status"]
        == "confirmed"
    )

    assert (
        transactions_dict[transaction_from_ecl_user_to_ecl_user2.id][
            "other_wallet_name"
        ]
        == "firstname ECL User 2 (nickname)"
    )
    assert (
        transactions_dict[transaction_from_ecl_user_to_ecl_user2.id]["type"] == "given"
    )
    assert transactions_dict[transaction_from_ecl_user_to_ecl_user2.id]["total"] == 600
    assert (
        transactions_dict[transaction_from_ecl_user_to_ecl_user2.id]["status"]
        == "confirmed"
    )

    assert (
        transactions_dict[transaction_from_store_to_ecl_user.id]["other_wallet_name"]
        == "Test Store"
    )
    assert (
        transactions_dict[transaction_from_store_to_ecl_user.id]["type"] == "received"
    )
    assert transactions_dict[transaction_from_store_to_ecl_user.id]["total"] == 700
    assert (
        transactions_dict[transaction_from_store_to_ecl_user.id]["status"]
        == "confirmed"
    )

    assert (
        transactions_dict[transaction_from_ecl_user2_to_ecl_user.id][
            "other_wallet_name"
        ]
        == "firstname ECL User 2 (nickname)"
    )
    assert (
        transactions_dict[transaction_from_ecl_user2_to_ecl_user.id]["type"]
        == "received"
    )
    assert transactions_dict[transaction_from_ecl_user2_to_ecl_user.id]["total"] == 800
    assert (
        transactions_dict[transaction_from_ecl_user2_to_ecl_user.id]["status"]
        == "confirmed"
    )


def ensure_qr_code_id_is_already_used(qr_code_id: str | UUID, client: TestClient):
    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "qr_code_id": str(qr_code_id),
            "walled_device_id": str(ecl_user_wallet_device.id),
            "total": 100,
            "creation": (datetime.now(UTC)).isoformat(),
            "store": True,
            "signature": "sign",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "QR Code already used"


def test_store_scan_already_used_qrcode(client: TestClient):
    """Test scanning an expired QR code"""
    ensure_qr_code_id_is_already_used(qr_code_id=used_qr_code.qr_code_id, client=client)


def test_store_scan_invalid_store_id(client: TestClient):
    qr_code_id = str(uuid4())

    response = client.post(
        f"/myeclpay/store/{uuid4()}/scan",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "qr_code_id": qr_code_id,
            "walled_device_id": str(ecl_user_wallet_device.id),
            "total": 100,
            "creation": datetime.now(UTC).isoformat(),
            "store": True,
            "signature": "sign",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Store does not exist"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_when_not_seller(client: TestClient):
    qr_code_id = str(uuid4())

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "qr_code_id": qr_code_id,
            "walled_device_id": str(ecl_user_wallet_device.id),
            "total": 100,
            "creation": datetime.now(UTC).isoformat(),
            "store": True,
            "signature": "sign",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "User does not have `can_bank` permission for this store"
    )

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_when_seller_but_can_not_bank(client: TestClient):
    qr_code_id = str(uuid4())

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={
            "Authorization": f"Bearer {store_seller_no_permission_user_access_token}",
        },
        json={
            "qr_code_id": qr_code_id,
            "walled_device_id": str(ecl_user_wallet_device.id),
            "total": 100,
            "creation": datetime.now(UTC).isoformat(),
            "store": True,
            "signature": "sign",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "User does not have `can_bank` permission for this store"
    )

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_invalid_wallet_device_id(client: TestClient):
    qr_code_id = str(uuid4())

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": qr_code_id,
            "walled_device_id": str(uuid4()),
            "total": 100,
            "creation": datetime.now(UTC).isoformat(),
            "store": True,
            "signature": "sign",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Wallet device does not exist"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_non_active_wallet_device_id(client: TestClient):
    qr_code_id = str(uuid4())

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": qr_code_id,
            "walled_device_id": str(ecl_user_wallet_device_unactive.id),
            "total": 100,
            "creation": datetime.now(UTC).isoformat(),
            "store": True,
            "signature": "sign",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Wallet device is not active"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_invalid_signature(client: TestClient):
    qr_code_id = str(uuid4())

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": qr_code_id,
            "walled_device_id": str(ecl_user_wallet_device.id),
            "total": 100,
            "creation": datetime.now(UTC).isoformat(),
            "store": True,
            "signature": "invalid signature",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid signature"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_with_non_store_qr_code(client: TestClient):
    qr_code_id = str(uuid4())

    qr_code_content = QRCodeContentBase(
        qr_code_id=qr_code_id,
        total=-1,
        creation=datetime.now(UTC),
        store=False,
        walled_device_id=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        compute_signable_data(qr_code_content),
    )

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": str(qr_code_content.qr_code_id),
            "walled_device_id": str(qr_code_content.walled_device_id),
            "total": qr_code_content.total,
            "creation": qr_code_content.creation.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"] == "QR Code is not intended to be scanned for a store"
    )

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_negative_total(client: TestClient):
    qr_code_id = str(uuid4())

    qr_code_content = QRCodeContentBase(
        qr_code_id=qr_code_id,
        total=-1,
        creation=datetime.now(UTC),
        store=True,
        walled_device_id=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        compute_signable_data(qr_code_content),
    )

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": str(qr_code_content.qr_code_id),
            "walled_device_id": str(qr_code_content.walled_device_id),
            "total": qr_code_content.total,
            "creation": qr_code_content.creation.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Total must be greater than 0"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_total_greater_than_max(client: TestClient):
    qr_code_id = str(uuid4())

    qr_code_content = QRCodeContentBase(
        qr_code_id=qr_code_id,
        total=4000,
        creation=datetime.now(UTC),
        store=True,
        walled_device_id=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        compute_signable_data(qr_code_content),
    )

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": str(qr_code_content.qr_code_id),
            "walled_device_id": str(qr_code_content.walled_device_id),
            "total": qr_code_content.total,
            "creation": qr_code_content.creation.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Total can not exceed 2000"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_missing_wallet(
    client: TestClient,
    mocker: MockerFixture,
):
    # This should never happen, as an user should never have a WalletDevice without an existing associated Wallet
    mocker.patch(
        "app.core.myeclpay.cruds_myeclpay.get_wallet",
        return_value=None,
    )

    qr_code_id = str(uuid4())

    qr_code_content = QRCodeContentBase(
        qr_code_id=qr_code_id,
        total=100,
        creation=datetime.now(UTC),
        store=True,
        walled_device_id=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        compute_signable_data(qr_code_content),
    )

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": str(qr_code_content.qr_code_id),
            "walled_device_id": str(qr_code_content.walled_device_id),
            "total": qr_code_content.total,
            "creation": qr_code_content.creation.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Could not find wallet associated with the debited wallet device"
    )

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_from_store_wallet(client: TestClient):
    qr_code_id = str(uuid4())

    qr_code_content = QRCodeContentBase(
        qr_code_id=qr_code_id,
        total=1100,
        creation=datetime.now(UTC),
        store=True,
        walled_device_id=store_wallet_device.id,
    )

    signature = store_wallet_device_private_key.sign(
        compute_signable_data(qr_code_content),
    )

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": str(qr_code_content.qr_code_id),
            "walled_device_id": str(qr_code_content.walled_device_id),
            "total": qr_code_content.total,
            "creation": qr_code_content.creation.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Stores are not allowed to make transaction by QR code"
    )

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


async def test_store_scan_store_from_wallet_with_old_cgu_version(client: TestClient):
    ecl_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    ecl_user_access_token = create_api_access_token(ecl_user)

    ecl_user_wallet = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.USER,
        balance=1000,  # 10€
    )
    await add_object_to_db(ecl_user_wallet)

    ecl_user_payment = models_myeclpay.UserPayment(
        user_id=ecl_user.id,
        wallet_id=ecl_user_wallet.id,
        accepted_cgu_signature=datetime.now(UTC),
        accepted_cgu_version=0,
    )
    await add_object_to_db(ecl_user_payment)

    ecl_user_wallet_device_private_key = Ed25519PrivateKey.generate()
    ecl_user_wallet_device = models_myeclpay.WalletDevice(
        id=uuid4(),
        name="Test device",
        wallet_id=ecl_user_wallet.id,
        ed25519_public_key=ecl_user_wallet_device_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ),
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.ACTIVE,
        activation_token=str(uuid4()),
    )
    await add_object_to_db(ecl_user_wallet_device)

    qr_code_id = str(uuid4())

    qr_code_content = QRCodeContentBase(
        qr_code_id=qr_code_id,
        total=1100,
        creation=datetime.now(UTC),
        store=True,
        walled_device_id=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        compute_signable_data(qr_code_content),
    )

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": str(qr_code_content.qr_code_id),
            "walled_device_id": str(qr_code_content.walled_device_id),
            "total": qr_code_content.total,
            "creation": qr_code_content.creation.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Debited user has not signed the latest CGU"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_insufficient_ballance(client: TestClient):
    qr_code_id = str(uuid4())

    qr_code_content = QRCodeContentBase(
        qr_code_id=qr_code_id,
        total=1100,
        creation=datetime.now(UTC),
        store=True,
        walled_device_id=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        compute_signable_data(qr_code_content),
    )

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": str(qr_code_content.qr_code_id),
            "walled_device_id": str(qr_code_content.walled_device_id),
            "total": qr_code_content.total,
            "creation": qr_code_content.creation.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient balance in the debited wallet"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


async def test_store_scan_store_successful_scan(client: TestClient):
    qr_code_id = str(uuid4())

    qr_code_content = QRCodeContentBase(
        qr_code_id=qr_code_id,
        total=500,
        creation=datetime.now(UTC),
        store=True,
        walled_device_id=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        compute_signable_data(qr_code_content),
    )

    async with TestingSessionLocal() as db:
        store_wallet_before_scan = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=store_wallet.id,
        )
        user_wallet_before_scan = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=ecl_user_wallet_device.wallet_id,
        )
    assert store_wallet_before_scan is not None
    assert user_wallet_before_scan is not None

    response = client.post(
        f"/myeclpay/store/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "qr_code_id": str(qr_code_content.qr_code_id),
            "walled_device_id": str(qr_code_content.walled_device_id),
            "total": qr_code_content.total,
            "creation": qr_code_content.creation.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 204

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)

    async with TestingSessionLocal() as db:
        store_wallet_after_scan = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=store_wallet.id,
        )
        user_wallet_after_scan = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=ecl_user_wallet_device.wallet_id,
        )
    assert store_wallet_after_scan is not None
    assert user_wallet_after_scan is not None

    # We check that the wallet balances were updated
    assert (
        store_wallet_after_scan.balance
        == store_wallet_before_scan.balance + qr_code_content.total
    )
    assert (
        user_wallet_after_scan.balance
        == user_wallet_before_scan.balance - qr_code_content.total
    )

    # We check that a transaction was created
    # TODO: verify that a transaction was created
