import base64
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.groups.groups_type import GroupType
from app.core.memberships import models_memberships
from app.core.myeclpay import cruds_myeclpay, models_myeclpay
from app.core.myeclpay.coredata_myeclpay import (
    MyECLPayBankAccountHolder,
)
from app.core.myeclpay.schemas_myeclpay import QRCodeContentData
from app.core.myeclpay.types_myeclpay import (
    TransactionStatus,
    TransactionType,
    TransferType,
    WalletDeviceStatus,
    WalletType,
)
from app.core.myeclpay.utils_myeclpay import LATEST_TOS
from app.core.users import models_users
from tests.commons import (
    add_coredata_to_db,
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
    get_TestingSessionLocal,
)

admin_user: models_users.CoreUser
admin_user_token: str
structure_manager_user: models_users.CoreUser
structure_manager_user_token: str
structure2_manager_user: models_users.CoreUser
structure2_manager_user_token: str

ecl_user: models_users.CoreUser
ecl_user_access_token: str
ecl_user_wallet: models_myeclpay.Wallet
ecl_user_wallet_device_private_key: Ed25519PrivateKey
ecl_user_wallet_device_public_key: Ed25519PublicKey
ecl_user_wallet_device: models_myeclpay.WalletDevice
ecl_user_wallet_device_inactive: models_myeclpay.WalletDevice
ecl_user_payment: models_myeclpay.UserPayment
ecl_user_transfer: models_myeclpay.Transfer

ecl_user2: models_users.CoreUser
ecl_user2_access_token: str
ecl_user2_wallet: models_myeclpay.Wallet
ecl_user2_wallet_device: models_myeclpay.WalletDevice
ecl_user2_payment: models_myeclpay.UserPayment

association_membership: models_memberships.CoreAssociationMembership
association_membership_user: models_memberships.CoreAssociationUserMembership
structure: models_myeclpay.Structure
structure2: models_myeclpay.Structure
store_wallet: models_myeclpay.Wallet
store: models_myeclpay.Store
store2: models_myeclpay.Store
store3: models_myeclpay.Store
store_wallet_device_private_key: Ed25519PrivateKey
store_wallet_device: models_myeclpay.WalletDevice


transaction_from_ecl_user_to_store: models_myeclpay.Transaction
transaction_from_ecl_user_to_ecl_user2: models_myeclpay.Transaction
transaction_from_store_to_ecl_user: models_myeclpay.Transaction
transaction_from_ecl_user2_to_ecl_user: models_myeclpay.Transaction

used_qr_code: models_myeclpay.UsedQRCode

invoice1: models_myeclpay.Invoice
invoice2: models_myeclpay.Invoice
invoice3: models_myeclpay.Invoice
invoice1_detail: models_myeclpay.InvoiceDetail
invoice2_detail: models_myeclpay.InvoiceDetail
invoice3_detail: models_myeclpay.InvoiceDetail

store_seller_can_bank_user: models_users.CoreUser
store_seller_no_permission_user_access_token: str
store_seller_can_bank_user_access_token: str
store_seller_can_cancel_user_access_token: str
store_seller_can_manage_sellers_user_access_token: str
store_seller_can_see_history_user_access_token: str


unregistered_ecl_user_access_token: str

UNIQUE_TOKEN = "UNIQUE_TOKEN"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global admin_user, admin_user_token
    admin_user = await create_user_with_groups(groups=[GroupType.admin])
    admin_user_token = create_api_access_token(admin_user)

    global association_membership
    association_membership = models_memberships.CoreAssociationMembership(
        id=uuid4(),
        name="Test Association Membership",
        manager_group_id=GroupType.BDE,
    )
    await add_object_to_db(association_membership)

    global \
        structure_manager_user, \
        structure_manager_user_token, \
        structure, \
        structure2_manager_user, \
        structure2_manager_user_token, \
        structure2

    structure_manager_user = await create_user_with_groups(groups=[])
    structure_manager_user_token = create_api_access_token(structure_manager_user)

    structure = models_myeclpay.Structure(
        id=uuid4(),
        name="Test Structure",
        creation=datetime.now(UTC),
        association_membership_id=association_membership.id,
        manager_user_id=structure_manager_user.id,
        short_id="ABC",
        siege_address_street="123 Test Street",
        siege_address_city="Test City",
        siege_address_zipcode="12345",
        siege_address_country="Test Country",
        siret="12345678901234",
        iban="FR76 1234 5678 9012 3456 7890 123",
        bic="AZERTYUIOP",
    )
    await add_object_to_db(structure)

    await add_coredata_to_db(
        MyECLPayBankAccountHolder(
            holder_structure_id=structure.id,
        ),
    )

    structure2_manager_user = await create_user_with_groups(groups=[])
    structure2_manager_user_token = create_api_access_token(structure2_manager_user)

    structure2 = models_myeclpay.Structure(
        id=uuid4(),
        name="Test Structure 2",
        creation=datetime.now(UTC),
        manager_user_id=structure_manager_user.id,
        short_id="XYZ",
        siege_address_street="456 Test Street",
        siege_address_city="Test City 2",
        siege_address_zipcode="67890",
        siege_address_country="Test Country 2",
        siret="23456789012345",
        iban="FR76 1234 5678 9012 3456 7890 123",
        bic="AZERTYUIOP",
    )
    await add_object_to_db(structure2)

    # ecl_user

    global ecl_user, ecl_user_access_token, association_membership_user
    ecl_user = await create_user_with_groups(
        groups=[],
    )
    ecl_user_access_token = create_api_access_token(ecl_user)

    association_membership_user = models_memberships.CoreAssociationUserMembership(
        id=uuid4(),
        user_id=ecl_user.id,
        association_membership_id=association_membership.id,
        start_date=datetime.now(UTC) - timedelta(days=1),
        end_date=datetime.now(UTC) + timedelta(days=1),
    )
    await add_object_to_db(association_membership_user)

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
    store2_wallet = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.STORE,
        balance=5000,  # 50€
    )
    await add_object_to_db(store2_wallet)
    store3_wallet = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.STORE,
        balance=5000,  # 50€
    )
    await add_object_to_db(store3_wallet)

    global store, store2
    store = models_myeclpay.Store(
        id=uuid4(),
        wallet_id=store_wallet.id,
        name="Test Store",
        structure_id=structure.id,
        creation=datetime.now(UTC),
    )
    await add_object_to_db(store)
    store2 = models_myeclpay.Store(
        id=uuid4(),
        wallet_id=store2_wallet.id,
        name="Test Store 2",
        structure_id=structure2.id,
        creation=datetime.now(UTC),
    )
    await add_object_to_db(store2)
    store3 = models_myeclpay.Store(
        id=uuid4(),
        wallet_id=store3_wallet.id,
        name="Test Store 3",
        structure_id=structure2.id,
        creation=datetime.now(UTC),
    )
    await add_object_to_db(store3)

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
        debited_wallet_id=ecl_user_wallet.id,
        debited_wallet_device_id=ecl_user_wallet_device.id,
        credited_wallet_id=store_wallet.id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=ecl_user2.id,
        total=500,  # 5€
        # We want to set a date that is not before a month ago
        # to be able to test refunds
        creation=datetime.now(UTC) - timedelta(days=2),
        status=TransactionStatus.CONFIRMED,
        store_note="transaction_from_ecl_user_to_store",
        qr_code_id=None,
    )
    await add_object_to_db(transaction_from_ecl_user_to_store)

    global transaction_from_ecl_user_to_ecl_user2
    transaction_from_ecl_user_to_ecl_user2 = models_myeclpay.Transaction(
        id=uuid4(),
        debited_wallet_id=ecl_user_wallet.id,
        debited_wallet_device_id=ecl_user_wallet_device.id,
        credited_wallet_id=ecl_user2_wallet.id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=ecl_user2.id,
        total=600,
        creation=datetime(2025, 5, 19, 12, 0, 0, tzinfo=UTC),
        status=TransactionStatus.CONFIRMED,
        store_note="transaction_from_ecl_user_to_ecl_user2",
        qr_code_id=None,
    )
    await add_object_to_db(transaction_from_ecl_user_to_ecl_user2)

    global transaction_from_store_to_ecl_user
    transaction_from_store_to_ecl_user = models_myeclpay.Transaction(
        id=uuid4(),
        debited_wallet_id=store_wallet.id,
        debited_wallet_device_id=store_wallet_device.id,
        credited_wallet_id=ecl_user_wallet.id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=ecl_user2.id,
        total=700,
        creation=datetime(2025, 5, 18, 12, 0, 0, tzinfo=UTC),
        status=TransactionStatus.CONFIRMED,
        store_note="transaction_from_store_to_ecl_user",
        qr_code_id=None,
    )
    await add_object_to_db(transaction_from_store_to_ecl_user)

    global transaction_from_ecl_user2_to_ecl_user
    transaction_from_ecl_user2_to_ecl_user = models_myeclpay.Transaction(
        id=uuid4(),
        debited_wallet_id=ecl_user2_wallet.id,
        debited_wallet_device_id=ecl_user2_wallet_device.id,
        credited_wallet_id=ecl_user_wallet.id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=ecl_user2.id,
        total=800,
        creation=datetime(2025, 5, 17, 12, 0, 0, tzinfo=UTC),
        status=TransactionStatus.CONFIRMED,
        store_note="transaction_from_ecl_user2_to_ecl_user",
        qr_code_id=None,
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
        qr_code_iat=datetime.now(UTC) - timedelta(days=1),
        qr_code_key=ecl_user2_wallet_device.id,
        qr_code_store=True,
        qr_code_tot=1000,
        signature="azertyuiop",
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

    global store_seller_can_cancel_user_access_token
    store_seller_can_cancel_user = await create_user_with_groups(
        groups=[],
    )
    store_seller_can_cancel_user_access_token = create_api_access_token(
        store_seller_can_cancel_user,
    )
    store_seller_can_cancel = models_myeclpay.Seller(
        user_id=store_seller_can_cancel_user.id,
        store_id=store.id,
        can_bank=False,
        can_see_history=False,
        can_cancel=True,
        can_manage_sellers=False,
    )
    await add_object_to_db(store_seller_can_cancel)

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

    global store_seller_can_see_history_user_access_token
    store_seller_can_see_history_user = await create_user_with_groups(
        groups=[],
    )
    store_seller_can_see_history_seller = models_myeclpay.Seller(
        user_id=store_seller_can_see_history_user.id,
        store_id=store.id,
        can_bank=False,
        can_see_history=True,
        can_cancel=False,
        can_manage_sellers=False,
    )
    await add_object_to_db(store_seller_can_see_history_seller)
    store_seller_can_see_history_user_access_token = create_api_access_token(
        store_seller_can_see_history_user,
    )

    global unregistered_ecl_user_access_token
    unregistered_ecl_user = await create_user_with_groups(
        groups=[],
    )
    unregistered_ecl_user_access_token = create_api_access_token(unregistered_ecl_user)

    global \
        invoice1, \
        invoice1_detail, \
        invoice2, \
        invoice2_detail, \
        invoice3, \
        invoice3_detail
    invoice1 = models_myeclpay.Invoice(
        id=uuid4(),
        reference=f"MYPAY{datetime.now(UTC).year}{structure.short_id}0001",
        structure_id=structure.id,
        creation=datetime.now(UTC),
        total=1000,
        paid=True,
        received=True,
        start_date=datetime.now(UTC) - timedelta(days=30),
        end_date=datetime.now(UTC) - timedelta(days=20),
    )
    await add_object_to_db(invoice1)
    invoice1_detail = models_myeclpay.InvoiceDetail(
        invoice_id=invoice1.id,
        store_id=store.id,
        total=1000,
    )
    await add_object_to_db(invoice1_detail)
    invoice2 = models_myeclpay.Invoice(
        id=uuid4(),
        reference=f"MYPAY{datetime.now(UTC).year}{structure.short_id}0002",
        structure_id=structure.id,
        creation=datetime.now(UTC),
        total=1000,
        paid=False,
        received=False,
        start_date=datetime.now(UTC) - timedelta(days=20),
        end_date=datetime.now(UTC) - timedelta(days=10),
    )
    await add_object_to_db(invoice2)
    invoice2_detail = models_myeclpay.InvoiceDetail(
        invoice_id=invoice2.id,
        store_id=store.id,
        total=1000,
    )
    await add_object_to_db(invoice2_detail)
    invoice3 = models_myeclpay.Invoice(
        id=uuid4(),
        reference=f"MYPAY{datetime.now(UTC).year}{structure2.short_id}0001",
        structure_id=structure2.id,
        creation=datetime.now(UTC),
        total=1000,
        paid=False,
        received=False,
        start_date=datetime.now(UTC) - timedelta(days=30),
        end_date=datetime.now(UTC) - timedelta(days=20),
    )
    await add_object_to_db(invoice3)
    invoice3_detail = models_myeclpay.InvoiceDetail(
        invoice_id=invoice3.id,
        store_id=store2.id,
        total=1000,
    )
    await add_object_to_db(invoice3_detail)


async def test_get_structures(client: TestClient):
    response = client.get(
        "/myeclpay/structures",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_create_structure(client: TestClient):
    response = client.post(
        "/myeclpay/structures",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "name": "Test Structure USEECL",
            "association_membership_id": str(association_membership.id),
            "manager_user_id": structure_manager_user.id,
            "short_id": "TUS",
            "siege_address_street": "123 Test Street",
            "siege_address_city": "Test City",
            "siege_address_zipcode": "12345",
            "siege_address_country": "Test Country",
            "siret": "12345678901236",
            "iban": "FR76 1234 5678 9012 3456 7890 124",
            "bic": "BNPAFRPPXXX",
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


async def test_patch_non_existing_structure(client: TestClient):
    response = client.patch(
        f"/myeclpay/structures/{uuid4()}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "name": "Test Structure Updated",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Structure does not exist"


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
        short_id="TSA",
        name="Test Structure add",
        creation=datetime.now(UTC),
        manager_user_id=structure_manager_user.id,
        siege_address_street="123 Test Street",
        siege_address_city="Test City",
        siege_address_zipcode="12345",
        siege_address_country="Test Country",
        siret="12345678901235",
        iban="FR76 1234 5678 9012 3456 7890 123",
        bic="AZERTYUIOP",
    )
    await add_object_to_db(new_structure)
    response = client.delete(
        f"/myeclpay/structures/{new_structure.id}",
        headers={"Authorization": f"Bearer {admin_user_token}"},
    )
    assert response.status_code == 204


async def test_transfer_non_existing_structure_manager(client: TestClient):
    response = client.post(
        f"/myeclpay/structures/{uuid4()}/init-manager-transfer",
        headers={"Authorization": f"Bearer {admin_user_token}"},
        json={
            "new_manager_user_id": ecl_user2.id,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Structure does not exist"


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


async def test_transfer_structure_manager_as_manager_but_invalid_new_manager_id(
    client: TestClient,
):
    response = client.post(
        f"/myeclpay/structures/{structure.id}/init-manager-transfer",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        json={
            "new_manager_user_id": str(uuid4()),
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "New manager user does not exist"


async def test_transfer_structure_manager_as_manager(
    client: TestClient,
    mocker: MockerFixture,
):
    new_structure = models_myeclpay.Structure(
        id=uuid4(),
        name="Test Structure 3",
        manager_user_id=structure_manager_user.id,
        creation=datetime.now(UTC),
        short_id="TS3",
        siege_address_street="123 Test Street",
        siege_address_city="Test City",
        siege_address_zipcode="12345",
        siege_address_country="Test Country",
        siret="12345678901235",
        iban="FR76 1234 5678 9012 3456 7890 123",
        bic="AZERTYUIOP",
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
        creation=datetime.now(UTC),
        wallet_id=new_wallet.id,
        name="Test Store Structure 2",
        structure_id=new_structure.id,
    )
    await add_object_to_db(new_store)
    new_wallet2 = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.STORE,
        balance=5000,
    )
    await add_object_to_db(new_wallet2)
    new_store2_where_new_manager_already_seller = models_myeclpay.Store(
        id=uuid4(),
        creation=datetime.now(UTC),
        wallet_id=new_wallet2.id,
        name="Test Store Structure 2 Where New Manager Already Seller",
        structure_id=new_structure.id,
    )
    await add_object_to_db(new_store2_where_new_manager_already_seller)
    seller = models_myeclpay.Seller(
        user_id=ecl_user2.id,
        store_id=new_store2_where_new_manager_already_seller.id,
        can_bank=True,
        can_see_history=False,
        can_cancel=False,
        can_manage_sellers=False,
    )
    await add_object_to_db(seller)

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

    result = client.get(
        "/myeclpay/users/me/stores",
        headers={"Authorization": f"Bearer {ecl_user2_access_token}"},
    )
    stores = result.json()
    assert len(stores) == 2
    assert str(new_store.id) in [store["id"] for store in stores]
    assert str(new_store2_where_new_manager_already_seller.id) in [
        store["id"] for store in stores
    ]
    store1 = next(store for store in stores if store["id"] == str(new_store.id))
    store2 = next(
        store
        for store in stores
        if store["id"] == str(new_store2_where_new_manager_already_seller.id)
    )
    assert store1["can_manage_sellers"] is True
    assert store2["can_manage_sellers"] is True


async def test_create_store_for_non_existing_structure(client: TestClient):
    response = client.post(
        f"/myeclpay/structures/{uuid4()}/stores",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        json={
            "name": "test_create_store Test Store",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Structure does not exist"


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


async def test_create_store_when_user_not_manager_of_structure(client: TestClient):
    response = client.post(
        f"/myeclpay/structures/{structure.id}/stores",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "name": "test_create_store Test Store",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not the manager for this structure"


async def test_create_store_with_name_already_exist(client: TestClient):
    response = client.post(
        f"/myeclpay/structures/{structure.id}/stores",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        json={
            "name": "Test Store",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Store with this name already exists in this structure"
    )


async def test_get_store_history_for_non_existing_store(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{uuid4()}/history",
        headers={"Authorization": f"Bearer {ecl_user2_access_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Store does not exist"


async def test_get_store_history_when_not_seller_can_see_history(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{store.id}/history",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to see the store history"
    )


async def test_get_store_history(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{store.id}/history",
        headers={
            "Authorization": f"Bearer {store_seller_can_see_history_user_access_token}",
        },
    )

    assert response.status_code == 200
    history_list = response.json()
    assert len(history_list) == 2

    history = {transaction["id"]: transaction for transaction in history_list}
    assert str(transaction_from_store_to_ecl_user.id) in history
    assert history[str(transaction_from_store_to_ecl_user.id)]["total"] == 700
    assert str(transaction_from_ecl_user_to_store.id) in history
    assert history[str(transaction_from_ecl_user_to_store.id)]["total"] == 500


async def test_get_store_history_with_date(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{store.id}/history",
        params={
            "start_date": "2025-05-18T00:00:00Z",
            "end_date": "2025-05-19T00:00:00Z",
        },
        headers={
            "Authorization": f"Bearer {store_seller_can_see_history_user_access_token}",
        },
    )

    assert response.status_code == 200
    history_list = response.json()
    assert len(history_list) == 1

    history = {transaction["id"]: transaction for transaction in history_list}
    assert str(transaction_from_store_to_ecl_user.id) in history
    assert history[str(transaction_from_store_to_ecl_user.id)]["total"] == 700


async def test_export_store_history_for_non_existing_store(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{uuid4()}/history/data-export",
        headers={"Authorization": f"Bearer {ecl_user2_access_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Store does not exist"


async def test_export_store_history_when_not_seller_can_see_history(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{store.id}/history/data-export",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"] == "User is not authorized to see the store history"
    )


async def test_export_store_history(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{store.id}/history/data-export",
        headers={
            "Authorization": f"Bearer {store_seller_can_see_history_user_access_token}",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert "store_history_Test Store" in response.headers["content-disposition"]

    # Verify CSV content
    csv_content = response.text
    lines = csv_content.split("\n")

    # Check header (skip BOM if present)
    header = lines[0].strip("\ufeff")
    assert "Date/Heure" in header
    assert "Type" in header
    assert "Autre partie" in header
    assert "Montant (€)" in header
    assert "Statut" in header
    assert "Vendeur" in header
    assert "Montant remboursé (€)" in header
    assert "Date remboursement" in header
    assert "Note magasin" in header

    # Check that we have 2 transactions (header + 2 data rows)
    # Filter out empty lines
    non_empty_lines = [line for line in lines if line.strip()]
    assert len(non_empty_lines) >= 3  # header + at least 2 transactions

    # Verify transactions are present in CSV
    csv_text = response.text
    assert "firstname ECL User 2 (nickname)" in csv_text
    assert "REÇU" in csv_text or "DONNÉ" in csv_text


async def test_export_store_history_with_date(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{store.id}/history/data-export",
        params={
            "start_date": "2025-05-18T00:00:00Z",
            "end_date": "2025-05-19T00:00:00Z",
        },
        headers={
            "Authorization": f"Bearer {store_seller_can_see_history_user_access_token}",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"

    # Verify filename contains date range
    content_disposition = response.headers["content-disposition"]
    assert "2025-05-18" in content_disposition
    assert "2025-05-19" in content_disposition

    # Verify CSV content has only 1 transaction
    csv_content = response.text
    lines = [line for line in csv_content.split("\n") if line.strip()]
    # header + 1 transaction
    assert len(lines) == 2


async def test_export_store_history_with_refund(client: TestClient):
    # Create a transaction and its refund
    transaction_to_refund = models_myeclpay.Transaction(
        id=uuid4(),
        debited_wallet_id=ecl_user_wallet.id,
        debited_wallet_device_id=ecl_user_wallet_device.id,
        credited_wallet_id=store_wallet.id,
        transaction_type=TransactionType.DIRECT,
        seller_user_id=ecl_user2.id,
        total=300,
        creation=datetime.now(UTC),
        status=TransactionStatus.REFUNDED,
        store_note="Transaction with refund",
        qr_code_id=None,
    )
    await add_object_to_db(transaction_to_refund)

    refund_test = models_myeclpay.Refund(
        id=uuid4(),
        transaction_id=transaction_to_refund.id,
        debited_wallet_id=store_wallet.id,
        credited_wallet_id=ecl_user_wallet.id,
        total=300,
        creation=datetime.now(UTC),
        seller_user_id=ecl_user2.id,
    )
    await add_object_to_db(refund_test)

    response = client.get(
        f"/myeclpay/stores/{store.id}/history/data-export",
        headers={
            "Authorization": f"Bearer {store_seller_can_see_history_user_access_token}",
        },
    )

    assert response.status_code == 200

    # Verify refund information is in CSV
    csv_content = response.text
    assert "3" in csv_content or "3.00" in csv_content  # Refund amount
    assert "Transaction with refund" in csv_content


async def test_export_store_history_encoding(client: TestClient):
    # Test that special characters (accents, etc.) are properly encoded
    response = client.get(
        f"/myeclpay/stores/{store.id}/history/data-export",
        headers={
            "Authorization": f"Bearer {store_seller_can_see_history_user_access_token}",
        },
    )

    assert response.status_code == 200

    # Verify UTF-8 BOM is present
    assert response.content.startswith(b"\xef\xbb\xbf")

    # Verify French characters are properly encoded
    csv_content = response.text
    assert "REÇU" in csv_content or "DONNÉ" in csv_content
    assert "€" in csv_content


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


async def test_update_store_non_existing(client: TestClient):
    response = client.patch(
        f"/myeclpay/stores/{uuid4()}",
        headers={
            "Authorization": f"Bearer {store_seller_can_bank_user_access_token}",
        },
        json={
            "name": "new name",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Store does not exist"


async def test_update_store_non_store_admin(client: TestClient):
    response = client.patch(
        f"/myeclpay/stores/{store.id}",
        headers={
            "Authorization": f"Bearer {store_seller_can_bank_user_access_token}",
        },
        json={
            "name": "new name",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not the manager for this structure"


async def test_delete_store_does_not_exist(client: TestClient):
    response = client.delete(
        f"/myeclpay/stores/{uuid4()}",
        headers={
            "Authorization": f"Bearer {structure_manager_user_token}",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Store does not exist"


async def test_delete_store_by_non_manager(client: TestClient):
    response = client.delete(
        f"/myeclpay/stores/{store.id}",
        headers={
            "Authorization": f"Bearer {ecl_user2_access_token}",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not the manager for this structure"


async def test_delete_store_with_history(client: TestClient):
    response = client.delete(
        f"/myeclpay/stores/{store.id}",
        headers={
            "Authorization": f"Bearer {structure_manager_user_token}",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Store has items in history and cannot be deleted anymore"
    )


async def test_delete_store(client: TestClient):
    store_id = uuid4()
    new_wallet = models_myeclpay.Wallet(
        id=store_id,
        type=WalletType.STORE,
        balance=5000,
    )
    await add_object_to_db(new_wallet)
    new_store = models_myeclpay.Store(
        id=store_id,
        creation=datetime.now(UTC),
        wallet_id=new_wallet.id,
        name="Test Store to Delete",
        structure_id=structure.id,
    )
    await add_object_to_db(new_store)
    sellet = models_myeclpay.Seller(
        user_id=structure_manager_user.id,
        store_id=new_store.id,
        can_bank=True,
        can_see_history=True,
        can_cancel=True,
        can_manage_sellers=True,
    )
    await add_object_to_db(sellet)

    response = client.delete(
        f"/myeclpay/stores/{store_id}",
        headers={
            "Authorization": f"Bearer {structure_manager_user_token}",
        },
    )
    assert response.status_code == 204


async def test_update_store(client: TestClient):
    new_wallet = models_myeclpay.Wallet(
        id=uuid4(),
        type=WalletType.STORE,
        balance=5000,
    )
    await add_object_to_db(new_wallet)
    new_store = models_myeclpay.Store(
        id=uuid4(),
        creation=datetime.now(UTC),
        wallet_id=new_wallet.id,
        name="Test Store Update",
        structure_id=structure.id,
    )
    await add_object_to_db(new_store)
    response = client.patch(
        f"/myeclpay/stores/{new_store.id}",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        json={
            "name": "Test Store Updated",
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


async def test_add_seller_for_non_existing_store(client: TestClient):
    response = client.post(
        f"/myeclpay/stores/{uuid4()}/sellers",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "user_id": ecl_user2.id,
            "can_bank": True,
            "can_see_history": True,
            "can_cancel": True,
            "can_manage_sellers": True,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Store does not exist"


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
    user = await create_user_with_groups(
        groups=[],
    )
    response = client.post(
        f"/myeclpay/stores/{store.id}/sellers",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
        json={
            "user_id": user.id,
            "can_bank": True,
            "can_see_history": True,
            "can_cancel": True,
            "can_manage_sellers": True,
        },
    )
    assert response.status_code == 201


async def test_add_seller_as_seller_without_permission(client: TestClient):
    user = await create_user_with_groups(
        groups=[],
    )
    response = client.post(
        f"/myeclpay/stores/{store.id}/sellers",
        headers={
            "Authorization": f"Bearer {store_seller_no_permission_user_access_token}",
        },
        json={
            "user_id": user.id,
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


async def test_add_already_existing_seller(client: TestClient):
    user = await create_user_with_groups(
        groups=[],
    )
    seller = models_myeclpay.Seller(
        user_id=user.id,
        store_id=store.id,
        can_bank=True,
        can_see_history=True,
        can_cancel=True,
        can_manage_sellers=False,
    )
    await add_object_to_db(seller)

    response = client.post(
        f"/myeclpay/stores/{store.id}/sellers",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
        json={
            "user_id": user.id,
            "can_bank": True,
            "can_see_history": True,
            "can_cancel": True,
            "can_manage_sellers": True,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Seller already exists"


async def test_get_sellers_for_non_existing_store(client: TestClient):
    response = client.get(
        f"/myeclpay/stores/{uuid4()}/sellers",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Store does not exist"


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


async def test_update_seller_of_non_existing_store(client: TestClient):
    response = client.patch(
        f"/myeclpay/stores/{uuid4()}/sellers/{store_seller_can_bank_user.id}",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "can_bank": False,
            "can_see_history": True,
            "can_cancel": False,
            "can_manage_sellers": False,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Store does not exist"


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


async def test_update_non_existing_seller(client: TestClient):
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
        f"/myeclpay/stores/{store.id}/sellers/{uuid4()}",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
        json={
            "can_bank": True,
            "can_see_history": True,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Seller does not exist"


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
            "can_see_history": True,
        },
    )
    assert response.status_code == 204

    response = client.get(
        f"/myeclpay/stores/{store.id}/sellers",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
    )
    assert response.status_code == 200
    assert len(response.json()) > 1
    seller_json = next(
        seller for seller in response.json() if seller["user_id"] == user.id
    )
    assert seller_json["can_bank"] is True
    assert seller_json["can_see_history"] is True
    assert seller_json["can_cancel"] is False
    assert seller_json["can_manage_sellers"] is False


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
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "User is the manager for this structure and cannot be updated as a seller"
    )


async def test_delete_seller_of_non_existing_store(client: TestClient):
    response = client.delete(
        f"/myeclpay/stores/{uuid4()}/sellers/{store_seller_can_bank_user.id}",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Store does not exist"


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


async def test_delete_non_existing_seller(client: TestClient):
    response = client.delete(
        f"/myeclpay/stores/{store.id}/sellers/{uuid4()}",
        headers={
            "Authorization": f"Bearer {store_seller_can_manage_sellers_user_access_token}",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Seller does not exist"


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
    assert response.status_code == 400
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


async def test_get_user_tos(client: TestClient):
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
        json={"accepted_tos_version": LATEST_TOS},
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

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    response = client.post(
        "/myeclpay/users/me/wallet/devices",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "name": "MySuperDevice",
            "ed25519_public_key": base64.b64encode(
                public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                ),
            ).decode("utf-8"),
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] is not None

    async with get_TestingSessionLocal()() as db:
        wallet_device = await db.get(
            models_myeclpay.WalletDevice,
            response.json()["id"],
        )
        assert wallet_device is not None
        assert wallet_device.ed25519_public_key == public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    response = client.get(
        f"/myeclpay/devices/activate?token={UNIQUE_TOKEN}",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert response.next_request is not None
    assert str(response.next_request.url).endswith(
        "calypsso/message?type=myeclpay_wallet_device_activation_success",
    )


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
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert response.next_request is not None
    assert str(response.next_request.url).endswith(
        "calypsso/message?type=myeclpay_wallet_device_already_activated_or_revoked",
    )


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
        ed25519_public_key=b"keytest_revoke_user_device",
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


def test_get_transactions_success_with_date(client: TestClient):
    """Test successfully getting user transactions"""
    response = client.get(
        "/myeclpay/users/me/wallet/history",
        params={
            "start_date": "2025-05-18T00:00:00Z",
            "end_date": "2025-05-19T23:59:59Z",
        },
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
    )
    assert response.status_code == 200

    transactions = response.json()
    assert len(transactions) == 2
    transactions_dict = {UUID(t["id"]): t for t in transactions}

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


def test_transfer_with_redirect_url_not_trusted(client: TestClient):
    """Test transferring with an unregistered user"""
    response = client.post(
        "/myeclpay/transfer/init",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
        json={
            "amount": 1000,
            "redirect_url": "http://localhost:3000/nottrusted",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Redirect URL is not trusted by hyperion"


def test_transfer_with_unregistered_user(client: TestClient):
    """Test transferring with an unregistered user"""
    response = client.post(
        "/myeclpay/transfer/init",
        headers={"Authorization": f"Bearer {unregistered_ecl_user_access_token}"},
        json={
            "amount": 1000,
            "redirect_url": "http://localhost:3000/payment_callback",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User is not registered for MyECL Pay"


def test_transfer_with_too_small_amount(client: TestClient):
    """Test transferring with an amount that is too small"""
    response = client.post(
        "/myeclpay/transfer/init",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "amount": 99,
            "redirect_url": "http://localhost:3000/payment_callback",
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Please give an amount in cents, greater than 1€."
    )


def test_transfer_with_too_big_amount(client: TestClient):
    """Test transferring with an amount that is too big"""
    response = client.post(
        "/myeclpay/transfer/init",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "amount": 8001,
            "redirect_url": "http://localhost:3000/payment_callback",
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
        "/myeclpay/transfer/init",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "amount": 1000,
            "redirect_url": "http://localhost:3000/payment_callback",
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


def test_redirect_from_ha_transfer_non_trusted_url(
    client: TestClient,
):
    response = client.get(
        "/myeclpay/transfer/redirect?url=http://localhost:3000/nottrusted",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Redirect URL is not trusted by hyperion"


def test_redirect_from_ha_transfer_trusted_url(
    client: TestClient,
):
    response = client.get(
        "/myeclpay/transfer/redirect?url=http://localhost:3000/payment_callback",
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert response.next_request is not None
    assert str(response.next_request.url) == "http://localhost:3000/payment_callback"


def ensure_qr_code_id_is_already_used(qr_code_id: str | UUID, client: TestClient):
    response = client.post(
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "id": str(qr_code_id),
            "key": str(ecl_user_wallet_device.id),
            "tot": 100,
            "iat": (datetime.now(UTC)).isoformat(),
            "store": True,
            "signature": "sign",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "QR Code already used"


def test_store_scan_already_used_qrcode(client: TestClient):
    """Test scanning an expired QR code"""
    ensure_qr_code_id_is_already_used(qr_code_id=used_qr_code.qr_code_id, client=client)


def test_store_scan_invalid_store_id(client: TestClient):
    qr_code_id = str(uuid4())

    response = client.post(
        f"/myeclpay/stores/{uuid4()}/scan",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "id": qr_code_id,
            "key": str(ecl_user_wallet_device.id),
            "tot": 100,
            "iat": datetime.now(UTC).isoformat(),
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
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={
            "id": qr_code_id,
            "key": str(ecl_user_wallet_device.id),
            "tot": 100,
            "iat": datetime.now(UTC).isoformat(),
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
        f"/myeclpay/stores/{store.id}/scan",
        headers={
            "Authorization": f"Bearer {store_seller_no_permission_user_access_token}",
        },
        json={
            "id": qr_code_id,
            "key": str(ecl_user_wallet_device.id),
            "tot": 100,
            "iat": datetime.now(UTC).isoformat(),
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
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "id": qr_code_id,
            "key": str(uuid4()),
            "tot": 100,
            "iat": datetime.now(UTC).isoformat(),
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
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "id": qr_code_id,
            "key": str(ecl_user_wallet_device_inactive.id),
            "tot": 100,
            "iat": datetime.now(UTC).isoformat(),
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
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "id": qr_code_id,
            "key": str(ecl_user_wallet_device.id),
            "tot": 100,
            "iat": datetime.now(UTC).isoformat(),
            "store": True,
            "signature": "invalid signature",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid signature"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_with_non_store_qr_code(client: TestClient):
    qr_code_id = uuid4()

    qr_code_content = QRCodeContentData(
        id=qr_code_id,
        tot=-1,
        iat=datetime.now(UTC),
        store=False,
        key=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        qr_code_content.model_dump_json().encode("utf-8"),
    )

    response = client.post(
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "id": str(qr_code_content.id),
            "key": str(qr_code_content.key),
            "tot": qr_code_content.tot,
            "iat": qr_code_content.iat.isoformat(),
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

    qr_code_content = QRCodeContentData(
        id=qr_code_id,
        tot=-1,
        iat=datetime.now(UTC),
        store=True,
        key=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        qr_code_content.model_dump_json().encode("utf-8"),
    )

    response = client.post(
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "id": str(qr_code_content.id),
            "key": str(qr_code_content.key),
            "tot": qr_code_content.tot,
            "iat": qr_code_content.iat.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Total must be greater than 0"

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

    qr_code_content = QRCodeContentData(
        id=qr_code_id,
        tot=100,
        iat=datetime.now(UTC),
        store=True,
        key=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        qr_code_content.model_dump_json().encode("utf-8"),
    )

    response = client.post(
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "id": str(qr_code_content.id),
            "key": str(qr_code_content.key),
            "tot": qr_code_content.tot,
            "iat": qr_code_content.iat.isoformat(),
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

    qr_code_content = QRCodeContentData(
        id=qr_code_id,
        tot=1100,
        iat=datetime.now(UTC),
        store=True,
        key=store_wallet_device.id,
    )

    signature = store_wallet_device_private_key.sign(
        qr_code_content.model_dump_json().encode("utf-8"),
    )

    response = client.post(
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "id": str(qr_code_content.id),
            "key": str(qr_code_content.key),
            "tot": qr_code_content.tot,
            "iat": qr_code_content.iat.isoformat(),
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

    qr_code_content = QRCodeContentData(
        id=qr_code_id,
        tot=1100,
        iat=datetime.now(UTC),
        store=True,
        key=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        qr_code_content.model_dump_json().encode("utf-8"),
    )

    response = client.post(
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "id": str(qr_code_content.id),
            "key": str(qr_code_content.key),
            "tot": qr_code_content.tot,
            "iat": qr_code_content.iat.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Debited user has not signed the latest TOS"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


def test_store_scan_store_insufficient_ballance(client: TestClient):
    qr_code_id = uuid4()

    qr_code_content = QRCodeContentData(
        id=qr_code_id,
        tot=3000,
        iat=datetime.now(UTC),
        store=True,
        key=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        qr_code_content.model_dump_json().encode("utf-8"),
    )

    response = client.post(
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "id": str(qr_code_content.id),
            "key": str(qr_code_content.key),
            "tot": qr_code_content.tot,
            "iat": qr_code_content.iat.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient balance in the debited wallet"

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)


async def test_store_scan_store_successful_scan(client: TestClient):
    qr_code_id = uuid4()

    qr_code_content = QRCodeContentData(
        id=qr_code_id,
        tot=500,
        iat=datetime.now(UTC),
        store=True,
        key=ecl_user_wallet_device.id,
    )

    signature = ecl_user_wallet_device_private_key.sign(
        qr_code_content.model_dump_json().encode("utf-8"),
    )

    async with get_TestingSessionLocal()() as db:
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
        f"/myeclpay/stores/{store.id}/scan",
        headers={"Authorization": f"Bearer {store_seller_can_bank_user_access_token}"},
        json={
            "id": str(qr_code_content.id),
            "key": str(qr_code_content.key),
            "tot": qr_code_content.tot,
            "iat": qr_code_content.iat.isoformat(),
            "store": qr_code_content.store,
            "signature": base64.b64encode(signature).decode("utf-8"),
        },
    )
    assert response.status_code == 201

    ensure_qr_code_id_is_already_used(qr_code_id=qr_code_id, client=client)

    async with get_TestingSessionLocal()() as db:
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
        == store_wallet_before_scan.balance + qr_code_content.tot
    )
    assert (
        user_wallet_after_scan.balance
        == user_wallet_before_scan.balance - qr_code_content.tot
    )

    # We check that a transaction was created
    # TODO: verify that a transaction was created


async def test_unknown_transaction_refund(client: TestClient):
    response = client.post(
        f"/myeclpay/transactions/{uuid4()}/refund",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={"complete_refund": True},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction does not exist"


async def test_transaction_refund_unconfirmed_transaction(client: TestClient):
    transaction_canceled = models_myeclpay.Transaction(
        id=uuid4(),
        debited_wallet_id=ecl_user_wallet.id,
        credited_wallet_id=store_wallet.id,
        total=100,
        status=TransactionStatus.CANCELED,
        creation=datetime.now(UTC),
        transaction_type=TransactionType.DIRECT,
        seller_user_id=store_seller_can_bank_user.id,
        debited_wallet_device_id=ecl_user_wallet_device.id,
        store_note="",
        qr_code_id=None,
    )
    await add_object_to_db(transaction_canceled)

    response = client.post(
        f"/myeclpay/transactions/{transaction_canceled.id}/refund",
        headers={"Authorization": f"Bearer {ecl_user_access_token}"},
        json={"complete_refund": True},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Transaction is not available for refund"


async def test_transaction_refund_unauthorized_user(client: TestClient):
    response = client.post(
        f"/myeclpay/transactions/{transaction_from_ecl_user_to_store.id}/refund",
        headers={"Authorization": f"Bearer {ecl_user2_access_token}"},
        json={"complete_refund": True},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "User does not have the permission to refund this transaction"
    )


async def test_transaction_refund_complete(client: TestClient):
    async with get_TestingSessionLocal()() as db:
        debited_wallet_before_refund = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=ecl_user_wallet.id,
        )
        credited_wallet_before_refund = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=store_wallet.id,
        )
    assert debited_wallet_before_refund is not None
    assert credited_wallet_before_refund is not None

    transaction = models_myeclpay.Transaction(
        id=uuid4(),
        debited_wallet_id=ecl_user_wallet.id,
        credited_wallet_id=store_wallet.id,
        total=100,
        status=TransactionStatus.CONFIRMED,
        creation=datetime.now(UTC),
        transaction_type=TransactionType.DIRECT,
        seller_user_id=store_seller_can_bank_user.id,
        debited_wallet_device_id=ecl_user_wallet_device.id,
        store_note="",
        qr_code_id=None,
    )
    await add_object_to_db(transaction)
    response = client.post(
        f"/myeclpay/transactions/{transaction.id}/refund",
        headers={
            "Authorization": f"Bearer {store_seller_can_cancel_user_access_token}",
        },
        json={"complete_refund": True},
    )
    assert response.status_code == 204

    async with get_TestingSessionLocal()() as db:
        transaction_after_refund = await cruds_myeclpay.get_transaction(
            db=db,
            transaction_id=transaction.id,
        )
        refund = await cruds_myeclpay.get_refund_by_transaction_id(
            db=db,
            transaction_id=transaction.id,
        )
        debited_wallet_after_refund = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=ecl_user_wallet.id,
        )
        credited_wallet_after_refund = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=store_wallet.id,
        )

    assert transaction_after_refund is not None
    assert refund is not None
    assert debited_wallet_after_refund is not None
    assert credited_wallet_after_refund is not None

    assert transaction_after_refund.status == TransactionStatus.REFUNDED
    assert refund.total == transaction.total
    assert refund.transaction_id == transaction.id
    assert (
        debited_wallet_after_refund.balance
        == debited_wallet_before_refund.balance + transaction.total
    )
    assert (
        credited_wallet_after_refund.balance
        == credited_wallet_before_refund.balance - transaction.total
    )


async def test_transaction_refund_partial_incomplete_amount(client: TestClient):
    response = client.post(
        f"/myeclpay/transactions/{transaction_from_ecl_user_to_store.id}/refund",
        headers={
            "Authorization": f"Bearer {store_seller_can_cancel_user_access_token}",
        },
        json={
            "complete_refund": False,
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Please provide an amount for the refund if it is not a complete refund"
    )


async def test_transaction_refund_partial_invalid_amount(client: TestClient):
    response = client.post(
        f"/myeclpay/transactions/{transaction_from_ecl_user_to_store.id}/refund",
        headers={
            "Authorization": f"Bearer {store_seller_can_cancel_user_access_token}",
        },
        json={
            "complete_refund": False,
            "amount": transaction_from_ecl_user_to_store.total + 1,
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Refund amount is greater than the transaction total"
    )

    response = client.post(
        f"/myeclpay/transactions/{transaction_from_ecl_user_to_store.id}/refund",
        headers={
            "Authorization": f"Bearer {store_seller_can_cancel_user_access_token}",
        },
        json={
            "complete_refund": False,
            "amount": 0,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Refund amount must be greater than 0"


async def test_transaction_refund_partial(client: TestClient):
    async with get_TestingSessionLocal()() as db:
        debited_wallet_before_refund = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=ecl_user_wallet.id,
        )
        credited_wallet_before_refund = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=store_wallet.id,
        )
    assert debited_wallet_before_refund is not None
    assert credited_wallet_before_refund is not None

    transaction = models_myeclpay.Transaction(
        id=uuid4(),
        debited_wallet_id=ecl_user_wallet.id,
        credited_wallet_id=store_wallet.id,
        total=100,
        status=TransactionStatus.CONFIRMED,
        creation=datetime.now(UTC),
        transaction_type=TransactionType.DIRECT,
        seller_user_id=store_seller_can_bank_user.id,
        debited_wallet_device_id=ecl_user_wallet_device.id,
        store_note="",
        qr_code_id=None,
    )
    await add_object_to_db(transaction)
    response = client.post(
        f"/myeclpay/transactions/{transaction.id}/refund",
        headers={
            "Authorization": f"Bearer {store_seller_can_cancel_user_access_token}",
        },
        json={
            "complete_refund": False,
            "amount": 50,
        },
    )
    assert response.status_code == 204

    async with get_TestingSessionLocal()() as db:
        transaction_after_refund = await cruds_myeclpay.get_transaction(
            db=db,
            transaction_id=transaction.id,
        )
        refund = await cruds_myeclpay.get_refund_by_transaction_id(
            db=db,
            transaction_id=transaction.id,
        )
        debited_wallet_after_refund = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=ecl_user_wallet.id,
        )
        credited_wallet_after_refund = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=store_wallet.id,
        )

    assert transaction_after_refund is not None
    assert refund is not None
    assert debited_wallet_after_refund is not None
    assert credited_wallet_after_refund is not None

    assert transaction_after_refund.status == TransactionStatus.REFUNDED
    assert refund.total == 50
    assert refund.transaction_id == transaction.id
    assert (
        debited_wallet_after_refund.balance == debited_wallet_before_refund.balance + 50
    )
    assert (
        credited_wallet_after_refund.balance
        == credited_wallet_before_refund.balance - 50
    )


async def test_get_invoices_as_random_user(client: TestClient):
    response = client.get(
        "/myeclpay/invoices",
        headers={"Authorization": f"Bearer {structure2_manager_user_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User is not the bank account holder"


async def test_get_invoices_as_bank_account_holder(client: TestClient):
    response = client.get(
        "/myeclpay/invoices",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 3


async def test_get_invoices_as_bank_account_holder_with_date(
    client: TestClient,
):
    response = client.get(
        "/myeclpay/invoices",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        params={
            "start_date": (datetime.now(UTC) - timedelta(days=40)).strftime(
                "%Y-%m-%dT%H:%M:%SZ",
            ),
            "end_date": (datetime.now(UTC) - timedelta(days=15)).strftime(
                "%Y-%m-%dT%H:%M:%SZ",
            ),
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_invoices_as_bank_account_holder_with_structure_id(
    client: TestClient,
):
    response = client.get(
        f"/myeclpay/invoices?structures_ids={structure2.id}",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_invoices_as_bank_account_holder_with_limit(
    client: TestClient,
):
    response = client.get(
        "/myeclpay/invoices",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        params={
            "page": 1,
            "page_size": 1,
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

    # Check that the first invoice is the most recent one
    invoices = response.json()
    assert invoices[0]["id"] == str(
        invoice2.id,
    )


async def test_get_structure_invoices_as_structure_manager(
    client: TestClient,
):
    response = client.get(
        f"/myeclpay/invoices/structures/{structure.id}",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_generate_invoice_as_structure_manager(
    client: TestClient,
):
    response = client.post(
        f"/myeclpay/invoices/structures/{structure.id}",
        headers={"Authorization": f"Bearer {structure2_manager_user_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User is not the bank account holder"


async def test_generate_invoice_as_bank_account_holder(
    client: TestClient,
):
    response = client.post(
        f"/myeclpay/invoices/structures/{structure2.id}",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )

    assert response.status_code == 201
    assert response.json()["id"] is not None
    assert response.json()["structure_id"] == str(structure2.id)
    assert (
        response.json()["reference"]
        == f"PAY{datetime.now(UTC).year}{structure2.short_id}0002"
    )

    assert response.json()["total"] == 9000

    invoices = client.get(
        f"/myeclpay/invoices/structures/{structure2.id}",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )
    assert len(invoices.json()) == 2


async def test_empty_invoice_on_null_details(
    client: TestClient,
):
    response = client.post(
        f"/myeclpay/invoices/structures/{structure2.id}",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No invoice to create"


async def test_update_invoice_paid_status_as_structure_manager(
    client: TestClient,
):
    response = client.patch(
        f"/myeclpay/invoices/{invoice3.id}/paid",
        headers={"Authorization": f"Bearer {structure2_manager_user_token}"},
        params={"paid": True},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User is not the bank account holder"


async def test_update_invoice_paid_status_as_bank_account_holder(
    client: TestClient,
):
    response = client.patch(
        f"/myeclpay/invoices/{invoice2.id}/paid",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        params={"paid": True},
    )

    assert response.status_code == 204, response.text

    async with get_TestingSessionLocal()() as db:
        invoice = await cruds_myeclpay.get_invoice_by_id(
            db=db,
            invoice_id=invoice2.id,
        )
        assert invoice is not None
        assert invoice.paid is True

    response = client.patch(
        f"/myeclpay/invoices/{invoice2.id}/paid",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
        params={"paid": False},
    )

    assert response.status_code == 204

    async with get_TestingSessionLocal()() as db:
        invoice = await cruds_myeclpay.get_invoice_by_id(
            db=db,
            invoice_id=invoice2.id,
        )
        assert invoice is not None
        assert invoice.paid is False


async def test_update_invoice_received_status_as_structure_manager(
    client: TestClient,
):
    async with get_TestingSessionLocal()() as db:
        await cruds_myeclpay.update_invoice_paid_status(
            db=db,
            invoice_id=invoice2.id,
            paid=True,
        )
        await db.commit()
        invoice = await cruds_myeclpay.get_invoice_by_id(
            db=db,
            invoice_id=invoice2.id,
        )
        assert invoice is not None

        store_wallet = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=invoice.details[0].store.wallet_id,
        )
        assert store_wallet is not None
        store_balance = store_wallet.balance

    response = client.patch(
        f"/myeclpay/invoices/{invoice2.id}/received",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )
    assert response.status_code == 204, response.text

    async with get_TestingSessionLocal()() as db:
        invoice = await cruds_myeclpay.get_invoice_by_id(
            db=db,
            invoice_id=invoice2.id,
        )
        assert invoice is not None
        assert invoice.received is True

        store_wallet = await cruds_myeclpay.get_wallet(
            db=db,
            wallet_id=invoice.details[0].store.wallet_id,
        )
        assert store_wallet is not None
        assert store_wallet.balance == store_balance - invoice.details[0].total

        withdrawals = await cruds_myeclpay.get_withdrawals_by_wallet_id(
            db=db,
            wallet_id=store_wallet.id,
        )
        assert len(withdrawals) == 1
        assert withdrawals[0].total == invoice.details[0].total


async def test_delete_paid_invoice(
    client: TestClient,
):
    response = client.delete(
        f"/myeclpay/invoices/{invoice2.id}",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )
    assert response.status_code == 400, response.text
    assert (
        response.json()["detail"]
        == "Cannot delete an invoice that has already been paid"
    )


async def test_delete_invoice(
    client: TestClient,
):
    response = client.delete(
        f"/myeclpay/invoices/{invoice3.id}",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )
    assert response.status_code == 204, response.text

    response = client.get(
        "/myeclpay/invoices",
        headers={"Authorization": f"Bearer {structure_manager_user_token}"},
    )
    assert response.status_code == 200
    assert not any(invoice["id"] == invoice3.id for invoice in response.json())
