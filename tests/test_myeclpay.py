from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.myeclpay import models_myeclpay
from app.core.myeclpay.types_myeclpay import (
    TransactionStatus,
    TransactionType,
    TransferType,
    WalletDeviceStatus,
    WalletType,
)
from app.types.membership import AvailableAssociationMembership
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

ecl_user: models_core.CoreUser
ecl_user_access_token: str
ecl_user_wallet: models_myeclpay.Wallet
ecl_user_wallet_device: models_myeclpay.WalletDevice
ecl_user_payment: models_myeclpay.UserPayment
ecl_user_transfer: models_myeclpay.Transfer

ecl_user2: models_core.CoreUser
ecl_user2_access_token: str
ecl_user2_wallet: models_myeclpay.Wallet
ecl_user2_wallet_device: models_myeclpay.WalletDevice
ecl_user2_payment: models_myeclpay.UserPayment

store_wallet: models_myeclpay.Wallet
store: models_myeclpay.Store
store_wallet_device: models_myeclpay.WalletDevice


transaction_from_ecl_user_to_store: models_myeclpay.Transaction
transaction_from_ecl_user_to_ecl_user2: models_myeclpay.Transaction
transaction_from_store_to_ecl_user: models_myeclpay.Transaction
transaction_from_ecl_user2_to_ecl_user: models_myeclpay.Transaction


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
        balance=2000,  # 20€
    )
    await add_object_to_db(ecl_user_wallet)

    global ecl_user_payment
    ecl_user_payment = models_myeclpay.UserPayment(
        user_id=ecl_user.id,
        wallet_id=ecl_user_wallet.id,
        accepted_cgu_signature=datetime.now(UTC),
        accepted_cgu_version=1,
    )
    await add_object_to_db(ecl_user_payment)

    global ecl_user_wallet_device
    ecl_user_wallet_device = models_myeclpay.WalletDevice(
        id=uuid4(),
        name="Test device",
        wallet_id=ecl_user_wallet.id,
        public_rsa_key="public_rsa_key",
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.ACTIVE,
        activation_token="activation_token",
    )
    await add_object_to_db(ecl_user_wallet_device)

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
        accepted_cgu_version=1,
    )
    await add_object_to_db(ecl_user2_payment)

    global ecl_user2_wallet_device
    ecl_user2_wallet_device = models_myeclpay.WalletDevice(
        id=uuid4(),
        name="Test device",
        wallet_id=ecl_user2_wallet.id,
        public_rsa_key="public_rsa_key",
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.ACTIVE,
        activation_token="activation_token",
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
    global store_wallet_device
    store_wallet_device = models_myeclpay.WalletDevice(
        id=uuid4(),
        name="Store test device",
        wallet_id=store_wallet.id,
        public_rsa_key="public_rsa_key",
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
        type=TransactionType.DIRECT,
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
        type=TransactionType.DIRECT,
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
        type=TransactionType.DIRECT,
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
        type=TransactionType.DIRECT,
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


async def test_register_user_new(client: TestClient):
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
    assert (
        response.json()["detail"] == "You have already signed a more recent CGU version"
    )

    response = client.post(
        "/myeclpay/users/me/register",
        headers={"Authorization": f"Bearer {unregistred_ecl_user_access_token}"},
        json={"accepted_cgu_version": 2},
    )
    assert response.status_code == 204

    response = client.post(
        "/myeclpay/users/me/register",
        headers={"Authorization": f"Bearer {unregistred_ecl_user_access_token}"},
        json={"accepted_cgu_version": 2},
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"] == "You have already signed a more recent CGU version"
    )


async def test_get_transactions_unregistered(client: TestClient):
    unregistred_ecl_user = await create_user_with_groups(
        groups=[GroupType.student],
    )
    unregistred_ecl_user_access_token = create_api_access_token(unregistred_ecl_user)

    response = client.get(
        "/myeclpay/users/me/wallet/transactions",
        headers={"Authorization": f"Bearer {unregistred_ecl_user_access_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


def test_get_transactions_success(client: TestClient):
    """Test successfully getting user transactions"""
    response = client.get(
        "/myeclpay/users/me/wallet/transactions",
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
