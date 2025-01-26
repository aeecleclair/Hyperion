import base64
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
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
from app.core.myeclpay.utils_myeclpay import LATEST_TOS, compute_signable_data
from app.types.membership import AvailableAssociationMembership
from tests.commons import (
    TestingSessionLocal,
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_core.CoreUser
admin_user_token: str
structure_manager_user: models_core.CoreUser
structure_manager_user_token: str

ecl_user: models_core.CoreUser
ecl_user_access_token: str
ecl_user_wallet: models_myeclpay.Wallet
ecl_user_wallet_device_private_key: Ed25519PrivateKey
ecl_user_wallet_device_public_key: Ed25519PublicKey
ecl_user_wallet_device: models_myeclpay.WalletDevice
ecl_user_wallet_device_inactive: models_myeclpay.WalletDevice
ecl_user_payment: models_myeclpay.UserPayment
ecl_user_transfer: models_myeclpay.Transfer

ecl_user2: models_core.CoreUser
ecl_user2_access_token: str
ecl_user2_wallet: models_myeclpay.Wallet
ecl_user2_wallet_device: models_myeclpay.WalletDevice
ecl_user2_payment: models_myeclpay.UserPayment


structure: models_myeclpay.Structure
store_wallet: models_myeclpay.Wallet
store: models_myeclpay.Store
store_wallet_device_private_key: Ed25519PrivateKey
store_wallet_device: models_myeclpay.WalletDevice


transaction_from_ecl_user_to_store: models_myeclpay.Transaction
transaction_from_ecl_user_to_ecl_user2: models_myeclpay.Transaction
transaction_from_store_to_ecl_user: models_myeclpay.Transaction
transaction_from_ecl_user2_to_ecl_user: models_myeclpay.Transaction

used_qr_code: models_myeclpay.UsedQRCode


store_seller_can_bank_user: models_core.CoreUser
store_seller_no_permission_user_access_token: str
store_seller_can_bank_user_access_token: str
store_seller_can_manage_sellers_user_access_token: str

unregistered_ecl_user_access_token: str

UNIQUE_TOKEN = "UNIQUE_TOKEN"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user, admin_user_token
    admin_user = await create_user_with_groups(groups=[GroupType.admin])
    admin_user_token = create_api_access_token(admin_user)

    global structure_manager_user, structure_manager_user_token, structure

    structure_manager_user = await create_user_with_groups(groups=[])
    structure_manager_user_token = create_api_access_token(structure_manager_user)
    structure = models_myeclpay.Structure(
        id=uuid4(),
        name="Test Structure",
        membership=AvailableAssociationMembership.aeecl,
        manager_user_id=structure_manager_user.id,
    )

    await add_object_to_db(structure)

    # ecl_user

    global ecl_user, ecl_user_access_token
    ecl_user = await create_user_with_groups(
        groups=[],
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
        accepted_tos_signature=datetime.now(UTC),
        accepted_tos_version=LATEST_TOS,
    )
    await add_object_to_db(ecl_user_payment)

    global \
        ecl_user_wallet_device, \
        ecl_user_wallet_device_private_key, \
        ecl_user_wallet_device_public_key, \
        ecl_user_wallet_device_inactive
    ecl_user_wallet_device_private_key = Ed25519PrivateKey.generate()
    ecl_user_wallet_device_public_key = ecl_user_wallet_device_private_key.public_key()
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
    ecl_user_wallet_device_inactive = models_myeclpay.WalletDevice(
        id=uuid4(),
        name="Test device inactive",
        wallet_id=ecl_user_wallet.id,
        ed25519_public_key=b"key",
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.INACTIVE,
        activation_token="activation_token_ecl_user_wallet_device_inactive",
    )
    await add_object_to_db(ecl_user_wallet_device_inactive)

    # ecl_user2
    global ecl_user2, ecl_user2_access_token
    ecl_user2 = await create_user_with_groups(
        firstname="firstname",
        name="ECL User 2",
        nickname="nickname",
        groups=[GroupType.BDE],
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
        accepted_tos_signature=datetime.now(UTC),
        accepted_tos_version=LATEST_TOS,
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
        structure_id=structure.id,
    )
    await add_object_to_db(store)
    manager_as_admin = models_myeclpay.Seller(
        user_id=structure_manager_user.id,
        store_id=store.id,
        can_bank=True,
        can_see_history=True,
        can_cancel=True,
        can_manage_sellers=True,
    )
    await add_object_to_db(manager_as_admin)

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
        confirmed=True,
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
        groups=[],
    )
    store_seller_no_permission_user_access_token = create_api_access_token(
        store_seller_no_permission_user,
    )
    store_seller_no_permission = models_myeclpay.Seller(
        user_id=store_seller_no_permission_user.id,
        store_id=store.id,
        can_bank=False,
        can_see_history=False,
        can_cancel=False,
        can_manage_sellers=False,
    )
    await add_object_to_db(store_seller_no_permission)

    global store_seller_can_bank_user_access_token, store_seller_can_bank_user
    store_seller_can_bank_user = await create_user_with_groups(
        groups=[],
    )
    store_seller_can_bank_user_access_token = create_api_access_token(
        store_seller_can_bank_user,
    )
    store_seller_can_bank = models_myeclpay.Seller(
        user_id=store_seller_can_bank_user.id,
        store_id=store.id,
        can_bank=True,
        can_see_history=False,
        can_cancel=False,
        can_manage_sellers=False,
    )
    await add_object_to_db(store_seller_can_bank)

    global store_seller_can_manage_sellers_user_access_token
    store_seller_can_manage_sellers_user = await create_user_with_groups(
        groups=[],
    )
    store_seller_can_manage_sellers_user_access_token = create_api_access_token(
        store_seller_can_manage_sellers_user,
    )
    store_seller_can_manage_sellers = models_myeclpay.Seller(
        user_id=store_seller_can_manage_sellers_user.id,
        store_id=store.id,
        can_bank=False,
        can_see_history=False,
        can_cancel=False,
        can_manage_sellers=True,
    )
    await add_object_to_db(store_seller_can_manage_sellers)

    global unregistered_ecl_user_access_token
    unregistered_ecl_user = await create_user_with_groups(
        groups=[],
    )
    unregistered_ecl_user_access_token = create_api_access_token(unregistered_ecl_user)


async def test_get_structures(client: TestClient):
    response = client.get(
        "/myeclpay/structures",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_create_structure(client: TestClient):
    response = client.post(
        "/myeclpay/structures",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "name": "Test Structure USEECL",
            "membership": AvailableAssociationMembership.useecl,
            "manager_user_id": structure_manager_user.id,
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] is not None


async def test_patch_structure_as_lambda(client: TestClient):
    response = client.patch(
        f"/myeclpay/structures/{structure.id}",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "name": "Test Structure Updated",
        },
    )
    assert response.status_code == 403


async def test_patch_structure_as_admin(client: TestClient):
    response = client.patch(
        f"/myeclpay/structures/{structure.id}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "name": "Test Structure Updated",
        },
    )
    assert response.status_code == 204


async def test_delete_structure_as_lambda(client: TestClient):
    response = client.delete(
        f"/myeclpay/structures/{structure.id}",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 403


async def test_delete_structure_as_admin_with_stores(client: TestClient):
    response = client.delete(
        f"/myeclpay/structures/{structure.id}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Structure has stores"


async def test_delete_structure_as_admin(client: TestClient):
    new_structure = models_myeclpay.Structure(
        id=uuid4(),
        name="Test Structure 2",
        membership=AvailableAssociationMembership.aeecl,
        manager_user_id=structure_manager_user.id,
    )
    await add_object_to_db(new_structure)
    response = client.delete(
        f"/myeclpay/structures/{new_structure.id}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 204


async def test_transfer_structure_manager_as_admin(client: TestClient):
    response = client.post(
        f"/myeclpay/structures/{structure.id}/init-manager-transfer",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "new_manager_user_id": ecl_user2.id,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not the manager for this structure"


async def test_transfer_structure_manager_with_wrong_token(client: TestClient):
    tranfert = models_myeclpay.StructureManagerTransfert(
        structure_id=structure.id,
        user_id=ecl_user2.id,
        confirmation_token="RANDOM_TOKEN",
        valid_until=datetime.now(UTC),
    )
    await add_object_to_db(tranfert)

    response = client.get(
        "/myeclpay/structures/confirm-manager-transfer",
        params={"token": "WRONG_TOKEN"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Request does not exist"

    response = client.get(
        "/myeclpay/structures/confirm-manager-transfer",
        params={"token": "RANDOM_TOKEN"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Request has expired"


async def test_transfer_structure_manager_as_manager(
    client: TestClient,
    mocker: MockerFixture,
):
    new_structure = models_myeclpay.Structure(
        id=uuid4(),
        name="Test Structure 2",
        membership=AvailableAssociationMembership.aeecl,
        manager_user_id=structure_manager_user.id,
    )
    await add_object_to_db(new_structure)
    new_wallet = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.STORE,
        balance=5000,
    )
    await add_object_to_db(new_wallet)
    new_store = models_myeclpay.Store(
        id=uuid4(),
        wallet_id=new_wallet.id,
        name="Test Store Structure 2",
        structure_id=new_structure.id,
    )
    await add_object_to_db(new_store)

    await add_object_to_db(new_structure)
    mocker.patch(
        "app.core.users.endpoints_users.security.generate_token",
        return_value=UNIQUE_TOKEN,
    )
    response = client.post(
        f"/myeclpay/structures/{new_structure.id}/init-manager-transfer",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        json={
            "new_manager_user_id": ecl_user2.id,
        },
    )
    assert response.status_code == 201

    response = client.get(
        "/myeclpay/structures/confirm-manager-transfer",
        params={"token": UNIQUE_TOKEN},
    )
    assert response.status_code == 200

    stores = client.get(
        "/myeclpay/users/me/stores",
        headers={"Authorization": f"Bearer {ecl_user2_access_token}"},
    )
    stores_ids = [store["id"] for store in stores.json()]
    assert str(new_store.id) in stores_ids


async def test_create_store(client: TestClient):
    response = client.post(
        f"/myeclpay/structures/{structure.id}/stores",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        json={
            "name": "test_create_store Test Store",
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] is not None

    stores = client.get(
        "/myeclpay/users/me/stores",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )
    stores_ids = [store["id"] for store in stores.json()]
    assert response.json()["id"] in stores_ids


async def test_get_stores_as_lambda(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/stores",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


async def test_get_stores_as_seller(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/stores",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_stores_as_manager(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/stores",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) > 1


async def test_update_store_non_store_admin(client: TestClient):
    response = client.patch(
        f"/myeclpay/stores/{store.id}",
        headers={
            "Authorization": f"Bearer {store_seller_can_bank_user_access_token}",
        },
        json={
            "name": "new name",
            "membership": AvailableAssociationMembership.aeecl,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not the manager for this structure"


async def test_update_store(client: TestClient):
    new_wallet = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.STORE,
        balance=5000,
    )
    await add_object_to_db(new_wallet)
    new_store = models_myeclpay.Store(
        id=uuid4(),
        wallet_id=new_wallet.id,
        name="Test Store 2",
        structure_id=structure.id,
    )
    await add_object_to_db(new_store)
    response = client.patch(
        f"/myeclpay/stores/{new_store.id}",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        json={
            "name": "Test Store 2 Updated",
        },
    )
    assert response.status_code == 204


async def test_get_user_stores(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/stores",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
    )
    assert response.status_code == 200
    # We want to make sure the user have at least a store
    # to be sure that the method was correctly tested
    assert len(response.json()) > 0


async def test_add_seller_as_lambda(client: TestClient):
    response = client.post(
        f"/myeclpay/stores/{store.id}/sellers",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "user_id": ecl_user2.id,
            "can_bank": True,
            "can_see_history": True,
            "can_cancel": True,
            "can_manage_sellers": True,
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User does not have the permission to manage sellers"
    )


async def test_add_seller_as_seller_with_permission(client: TestClient):
    response = client.post(
        f"/myeclpay/stores/{store.id}/sellers",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
        json={
            "user_id": ecl_user2.id,
            "can_bank": True,
            "can_see_history": True,
            "can_cancel": True,
            "can_manage_sellers": True,
        },
    )
    assert response.status_code == 201


async def test_add_seller_as_seller_without_permission(client: TestClient):
    response = client.post(
        f"/myeclpay/stores/{store.id}/sellers",
        headers={
            "Authorization": f"Bearer {store_seller_no_permission_user_access_token}",
        },
        json={
            "user_id": ecl_user2.id,
            "can_bank": True,
            "can_see_history": True,
            "can_cancel": True,
            "can_manage_sellers": True,
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User does not have the permission to manage sellers"
    )


async def test_get_sellers_as_lambda(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{store.id}/sellers",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User does not have the permission to manage sellers"
    )


async def test_get_sellers_as_seller_with_permission(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{store.id}/sellers",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
    )
    assert response.status_code == 200
    assert len(response.json()) > 0


async def test_get_sellers_as_seller_without_permission(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{store.id}/sellers",
        headers={
            "Authorization": f"Bearer {store_seller_no_permission_user_access_token}",
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User does not have the permission to manage sellers"
    )


async def test_update_seller_as_lambda(client: TestClient):
    response = client.patch(
        f"/myeclpay/stores/{store.id}/sellers/{store_seller_can_bank_user.id}",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "can_bank": False,
            "can_see_history": True,
            "can_cancel": False,
            "can_manage_sellers": False,
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User does not have the permission to manage sellers"
    )


async def test_update_seller_as_seller_without_permission(client: TestClient):
    response = client.patch(
        f"/myeclpay/stores/{store.id}/sellers/{store_seller_can_bank_user.id}",
        headers={
            "Authorization": f"Bearer {store_seller_no_permission_user_access_token}",
        },
        json={
            "can_bank": True,
            "can_see_history": False,
            "can_cancel": False,
            "can_manage_sellers": False,
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User does not have the permission to manage sellers"
    )


async def test_update_seller_as_seller_with_permission(client: TestClient):
    user = await create_user_with_groups(
        groups=[],
    )
    seller = models_myeclpay.Seller(
        user_id=user.id,
        store_id=store.id,
        can_bank=False,
        can_see_history=False,
        can_cancel=False,
        can_manage_sellers=False,
    )
    await add_object_to_db(seller)
    response = client.patch(
        f"/myeclpay/stores/{store.id}/sellers/{user.id}",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
        json={
            "can_bank": True,
            "can_see_history": False,
            "can_cancel": False,
            "can_manage_sellers": False,
        },
    )
    assert response.status_code == 204


async def test_update_manager_seller(client: TestClient):
    response = client.patch(
        f"/myeclpay/stores/{store.id}/sellers/{structure_manager_user.id}",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
        json={
            "can_bank": True,
            "can_see_history": False,
            "can_cancel": False,
            "can_manage_sellers": False,
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User is the manager for this structure and cannot be updated as a seller"
    )


async def test_delete_seller_as_lambda(client: TestClient):
    response = client.delete(
        f"/myeclpay/stores/{store.id}/sellers/{store_seller_can_bank_user.id}",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User does not have the permission to manage sellers"
    )


async def test_delete_seller_as_seller_without_permission(client: TestClient):
    response = client.delete(
        f"/myeclpay/stores/{store.id}/sellers/{store_seller_can_bank_user.id}",
        headers={
            "Authorization": f"Bearer {store_seller_no_permission_user_access_token}",
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User does not have the permission to manage sellers"
    )


async def test_delete_seller_as_seller_with_permission(client: TestClient):
    user = await create_user_with_groups(
        groups=[],
    )
    seller = models_myeclpay.Seller(
        user_id=user.id,
        store_id=store.id,
        can_bank=False,
        can_see_history=False,
        can_cancel=False,
        can_manage_sellers=False,
    )
    await add_object_to_db(seller)
    response = client.delete(
        f"/myeclpay/stores/{store.id}/sellers/{user.id}",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
    )
    assert response.status_code == 204


async def test_delete_manager_seller(client: TestClient):
    response = client.delete(
        f"/myeclpay/stores/{store.id}/sellers/{structure_manager_user.id}",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User is the manager for this structure and cannot be deleted as a seller"
    )


async def test_get_tos_for_unregistered_user(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/tos",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


async def test_get_tos(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/tos",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["latest_tos_version"] == LATEST_TOS
    assert response.json()["accepted_tos_version"] == LATEST_TOS


async def test_register_new_user(client: TestClient):
    user_to_register = await create_user_with_groups(
        groups=[],
    )
    user_to_register_token = create_api_access_token(user_to_register)

    response = client.post(
        "/myeclpay/users/me/register",
        headers={"Authorization": f"Bearer {user_to_register_token}"},
    )
    assert response.status_code == 204

    response = client.post(
        "/myeclpay/users/me/register",
        headers={"Authorization": f"Bearer {user_to_register_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is already registered for MyECL Pay"


async def test_sign_tos_for_old_tos_version(client: TestClient):
    response = client.post(
        "/myeclpay/users/me/tos",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
        json={"accepted_tos_version": 0},
    )
    assert response.status_code == 400
    assert response.json()["detail"][:27] == "Only the latest TOS version"


async def test_sign_tos_for_unregistered_user(client: TestClient):
    response = client.post(
        "/myeclpay/users/me/tos",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
        json={"accepted_tos_version": 1},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


async def test_sign_tos(client: TestClient):
    unregistered_user = await create_user_with_groups(
        groups=[],
    )
    unregistered_user_token = create_api_access_token(unregistered_user)

    response = client.post(
        "/myeclpay/users/me/register",
        headers={"Authorization": f"Bearer {unregistered_user_token}"},
    )
    assert response.status_code == 204

    response = client.post(
        "/myeclpay/users/me/tos",
        headers={"Authorization": f"Bearer {unregistered_user_token}"},
        json={"accepted_tos_version": LATEST_TOS},
    )
    assert response.status_code == 204


async def test_get_user_devices_with_unregistred_user(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/wallet/devices",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


async def test_get_user_devices(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/wallet/devices",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_user_wallet_unregistred_user(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/wallet",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


async def test_get_user_wallet(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/wallet",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] is not None


async def test_get_user_device_non_existing_user(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/wallet/devices/f33a6034-0420-4c08-8afd-46ef662d0b28",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


async def test_get_user_device_non_existing_device(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/wallet/devices/f33a6034-0420-4c08-8afd-46ef662d0b28",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Wallet device does not exist"


async def test_get_user_device_with_device_from_an_other_user(client: TestClient):
    response = client.get(
        f"/myeclpay/users/me/wallet/devices/{store_wallet_device.id}",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Wallet device does not belong to the user"


async def test_get_user_device(client: TestClient):
    response = client.get(
        f"/myeclpay/users/me/wallet/devices/{ecl_user_wallet_device.id}",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] is not None


async def test_create_user_device_unregistred_user(client: TestClient):
    response = client.post(
        "/myeclpay/users/me/wallet/devices",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
        json={
            "name": "MyDevice",
            "ed25519_public_key": base64.b64encode(
                ecl_user_wallet_device_public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                ),
            ).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


async def test_create_and_activate_user_device(
    mocker: MockerFixture,
    client: TestClient,
) -> None:
    # NOTE: we don't want to mock app.core.security.generate_token but
    # app.core.users.endpoints_users.security.generate_token which is the imported version of the function
    mocker.patch(
        "app.core.users.endpoints_users.security.generate_token",
        return_value=UNIQUE_TOKEN,
    )

    response = client.post(
        "/myeclpay/users/me/wallet/devices",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "name": "MySuperDevice",
            "ed25519_public_key": base64.b64encode(
                ecl_user_wallet_device_public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                ),
            ).decode("utf-8"),
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] is not None

    response = client.get(
        f"/myeclpay/devices/activate?token={UNIQUE_TOKEN}",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200
    assert response.json() == "Wallet device activated"


async def test_activate_non_existing_device(
    client: TestClient,
) -> None:
    response = client.get(
        "/myeclpay/devices/activate?token=invalid_token",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Invalid token"


async def test_activate_already_activated_device(
    client: TestClient,
) -> None:
    response = client.get(
        "/myeclpay/devices/activate?token=activation_token_ecl_user_wallet_device",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Wallet device is already activated or revoked"


async def test_revoke_user_device_unregistered_user(
    client: TestClient,
) -> None:
    wallet_device_id = uuid4()
    response = client.post(
        f"/myeclpay/users/me/wallet/devices/{wallet_device_id}/revoke",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


async def test_revoke_user_device_device_does_not_exist(
    client: TestClient,
) -> None:
    wallet_device_id = uuid4()
    response = client.post(
        f"/myeclpay/users/me/wallet/devices/{wallet_device_id}/revoke",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Wallet device does not exist"


async def test_revoke_user_device_device_does_not_belong_to_user(
    client: TestClient,
) -> None:
    response = client.post(
        f"/myeclpay/users/me/wallet/devices/{ecl_user_wallet_device.id}/revoke",
        headers={"Authorization": f"Bearer {ecl_user2_access_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Wallet device does not belong to the user"


async def test_revoke_user_device(
    client: TestClient,
) -> None:
    wallet_device = models_myeclpay.WalletDevice(
        id=uuid4(),
        name="Will revoke device",
        wallet_id=ecl_user_wallet.id,
        ed25519_public_key=b"key",
        creation=datetime.now(UTC),
        status=WalletDeviceStatus.ACTIVE,
        activation_token="will_revoke_activation_token",
    )
    await add_object_to_db(wallet_device)
    response = client.post(
        f"/myeclpay/users/me/wallet/devices/{wallet_device.id}/revoke",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 204

    # We want to verify the device is now revoked
    response = client.get(
        "/myeclpay/users/me/wallet/devices/",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200
    returned_wallet_device = next(
        device for device in response.json() if device["id"] == str(wallet_device.id)
    )
    assert returned_wallet_device["status"] == "revoked"


async def test_get_transactions_unregistered(client: TestClient):
    response = client.get(
        "/myeclpay/users/me/wallet/history",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
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


def test_transfer_with_unregistered_user(client: TestClient):
    """Test transferring with an unregistered user"""
    response = client.post(
        "/myeclpay/transfer",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
        json={
            "amount": 1000,
            "transfer_type": "hello_asso",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


def test_transfer_with_too_small_amount(client: TestClient):
    """Test transferring with an amount that is too small"""
    response = client.post(
        "/myeclpay/transfer",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "amount": 99,
            "transfer_type": "hello_asso",
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"] == "Please give an amount in cents, greater than 1€."
    )


def test_transfer_with_too_big_amount(client: TestClient):
    """Test transferring with an amount that is too big"""
    response = client.post(
        "/myeclpay/transfer",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "amount": 8001,
            "transfer_type": "hello_asso",
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Wallet balance would exceed the maximum allowed balance"
    )


def test_hello_asso_transfer(
    client: TestClient,
    mocker: MockerFixture,
):
    """Test transferring with the hello_asso transfer type"""
    response = client.post(
        "/myeclpay/transfer",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "amount": 1000,
            "transfer_type": "hello_asso",
        },
    )
    assert response.status_code == 201
    assert response.json()["url"] == "https://some.url.fr/checkout"

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {"amount": 1000, "id": 123},
            "metadata": {
                "hyperion_checkout_id": "81c9ad91-f415-494a-96ad-87bf647df82c",
                "secret": "checkoutsecret",
            },
        },
    )
    assert response.status_code == 204


def test_non_hello_asso_transfer_without_receiver(client: TestClient):
    """Test transferring with a non-hello_asso transfer type as a non-BDE user"""
    response = client.post(
        "/myeclpay/transfer",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "amount": 1000,
            "transfer_type": "cash",
        },
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Please provide a receiver user id for this transfer type"
    )


def test_non_hello_asso_transfer_as_non_bde(client: TestClient):
    """Test transferring with a non-hello_asso transfer type as a non-BDE user"""
    response = client.post(
        "/myeclpay/transfer",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "amount": 1000,
            "transfer_type": "cash",
            "receiver_user_id": ecl_user2.id,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not allowed to approve this transfer"


def test_non_hello_asso_transfer_as_bde(client: TestClient):
    """Test transferring with a non-hello_asso transfer type as a BDE user"""
    response = client.post(
        "/myeclpay/transfer",
        headers={"Authorization": f"Bearer {ecl_user2_access_token}"},
        json={
            "amount": 1000,
            "transfer_type": "cash",
            "receiver_user_id": ecl_user.id,
        },
    )
    assert response.status_code == 201
    assert response.json()["url"] == ""


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
            "walled_device_id": str(ecl_user_wallet_device_inactive.id),
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
    qr_code_id = uuid4()

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
    qr_code_id = uuid4()

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
    qr_code_id = uuid4()

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

    qr_code_id = uuid4()

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
    qr_code_id = uuid4()

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


async def test_store_scan_store_from_wallet_with_old_tos_version(client: TestClient):
    ecl_user = await create_user_with_groups(
        groups=[],
    )

    ecl_user_wallet = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.USER,
        balance=1000,  # 10€
    )
    await add_object_to_db(ecl_user_wallet)

    ecl_user_payment = models_myeclpay.UserPayment(
        user_id=ecl_user.id,
        wallet_id=ecl_user_wallet.id,
        accepted_tos_signature=datetime.now(UTC),
        accepted_tos_version=0,
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

    qr_code_id = uuid4()

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
    assert response.json()["detail"] == "Debited user has not signed the latest TOS"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_insufficient_ballance(client: TestClient):
    qr_code_id = uuid4()

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
    qr_code_id = uuid4()

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
