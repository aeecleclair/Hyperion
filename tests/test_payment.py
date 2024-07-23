import uuid

import pytest_asyncio
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment import cruds_payment, models_payment, schemas_payment
from app.types.module import Module
from tests.commons import (
    TestingSessionLocal,
    add_object_to_db,
)

checkout_with_existing_checkout_payment: models_payment.Checkout
existing_checkout_payment: models_payment.CheckoutPayment
checkout: models_payment.Checkout

TEST_MODULE_ROOT = "tests"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global checkout_with_existing_checkout_payment
    checkout_with_existing_checkout_payment_id = uuid.uuid4()
    checkout_with_existing_checkout_payment = models_payment.Checkout(
        id=checkout_with_existing_checkout_payment_id,
        module=TEST_MODULE_ROOT,
        name="Test Payment",
        amount=100,
        hello_asso_checkout_id=1,
        hello_asso_order_id=1,
        secret="payment secret",
    )
    await add_object_to_db(checkout_with_existing_checkout_payment)

    global existing_checkout_payment
    existing_checkout_payment = models_payment.CheckoutPayment(
        id=uuid.uuid4(),
        checkout_id=checkout_with_existing_checkout_payment_id,
        paid_amount=100,
        hello_asso_payment_id=1,
    )
    await add_object_to_db(existing_checkout_payment)

    global checkout
    checkout = models_payment.Checkout(
        id=uuid.uuid4(),
        module="tests",
        name="Test Payment",
        amount=100,
        hello_asso_checkout_id=2,
        hello_asso_order_id=2,
        secret="secret",
    )
    await add_object_to_db(checkout)


def test_webhook_with_invalid_body(client: TestClient) -> None:
    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "invalid": "body",
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Could not validate the webhook body"}


def test_webhook_order(client: TestClient) -> None:
    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Order",
            "data": {},
        },
    )
    assert response.status_code == 204


def test_webhook_payment_for_already_received_payment(
    mocker: MockerFixture,
    client: TestClient,
) -> None:
    """
    This situation could happen if HelloAsso call our webhook multiple times for the same payment.
    """
    mocked_hyperion_security_logger = mocker.patch(
        "app.core.payment.endpoints_payment.hyperion_error_logger.debug",
    )

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {
                "id": existing_checkout_payment.hello_asso_payment_id,
                "amount": 100,
            },
            "metadata": {
                "hyperion_checkout_id": str(checkout_with_existing_checkout_payment.id),
                "secret": checkout_with_existing_checkout_payment.secret,
            },
        },
    )

    assert response.status_code == 204
    mocked_hyperion_security_logger.assert_called_once_with(
        f"Payment: ignoring webhook call for helloasso checkout payment id {existing_checkout_payment.hello_asso_payment_id} as it already exists in the database",
    )


def test_webhook_payment_without_metadata(
    client: TestClient,
) -> None:
    """
    We should ignore payments without metadata, which means they are not related to a checkout we initiated.
    """

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {
                "id": existing_checkout_payment.hello_asso_payment_id,
                "amount": 100,
            },
        },
    )

    assert response.status_code == 204


def test_webhook_payment_with_non_existing_checkout(
    client: TestClient,
) -> None:
    """
    We should ignore payments without metadata, which means they are not related to a checkout we initiated.
    """

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {
                "id": 3,
                "amount": 100,
            },
            "metadata": {
                # Non existing hyperion_checkout_id
                "hyperion_checkout_id": "8e7afb08-a152-4e8e-b1f1-251666d96dbb",
                "secret": "secret",
            },
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Could not find checkout 8e7afb08-a152-4e8e-b1f1-251666d96dbb in database",
    }


def test_webhook_payment_with_invalid_secret(
    client: TestClient,
) -> None:
    """
    We should ignore payments without metadata, which means they are not related to a checkout we initiated.
    """

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {
                "id": 3,
                "amount": 100,
            },
            "metadata": {
                "hyperion_checkout_id": str(checkout.id),
                "secret": "invalid secret",
            },
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Secret mismatch"}


async def test_webhook_payment(
    client: TestClient,
) -> None:
    # We will simulate a first payment of 0,7 € then a payment of 0,3 €

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {
                "id": 3,
                "amount": 70,
            },
            "metadata": {
                "hyperion_checkout_id": str(checkout.id),
                "secret": "secret",
            },
        },
    )

    assert response.status_code == 204

    async with TestingSessionLocal() as db:
        checkout_model = await cruds_payment.get_checkout_by_id(
            checkout_id=checkout.id,
            db=db,
        )
        assert checkout_model is not None
        assert len(checkout_model.payments) == 1
        assert checkout_model.payments[0].paid_amount == 70

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {
                "id": 4,
                "amount": 30,
            },
            "metadata": {
                "hyperion_checkout_id": str(checkout.id),
                "secret": "secret",
            },
        },
    )

    assert response.status_code == 204

    async with TestingSessionLocal() as db:
        checkout_model = await cruds_payment.get_checkout_by_id(
            checkout_id=checkout.id,
            db=db,
        )
        assert checkout_model is not None
        assert len(checkout_model.payments) == 2
        # The order of the payments is not guaranteed, we may need to change this assertion
        assert checkout_model.payments[0].paid_amount == 70
        assert checkout_model.payments[1].paid_amount == 30
        assert sum(payment.paid_amount for payment in checkout_model.payments) == 100


async def callback(
    checkout_payment: schemas_payment.CheckoutPayment, db: AsyncSession,
) -> None:
    pass


async def test_webhook_payment_callback(
    mocker: MockerFixture,
    client: TestClient,
) -> None:
    # We patch the callback to be able to check if it was called
    mocked_callback = mocker.patch(
        "tests.test_payment.callback",
    )

    # We patch the module_list to inject our custom test module
    test_module = Module(
        root=TEST_MODULE_ROOT,
        tag="Tests",
        default_allowed_groups_ids=[],
        payment_callback=callback,
    )
    mocker.patch(
        "app.core.payment.endpoints_payment.module_list",
        [test_module],
    )

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {
                "id": 5,
                "amount": 40,
            },
            "metadata": {
                "hyperion_checkout_id": str(checkout.id),
                "secret": "secret",
            },
        },
    )

    assert response.status_code == 204
    mocked_callback.assert_called_once()


async def test_webhook_payment_callback_fail(
    mocker: MockerFixture,
    client: TestClient,
) -> None:
    # We patch the callback to be able to check if it was called
    mocked_callback = mocker.patch(
        "tests.test_payment.callback",
        side_effect=ValueError("Test error"),
    )

    # We patch the module_list to inject our custom test module
    test_module = Module(
        root=TEST_MODULE_ROOT,
        tag="Tests",
        default_allowed_groups_ids=[],
        payment_callback=callback,
    )
    mocker.patch(
        "app.core.payment.endpoints_payment.module_list",
        [test_module],
    )

    mocked_hyperion_security_logger = mocker.patch(
        "app.core.payment.endpoints_payment.hyperion_error_logger.error",
    )

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {
                "id": 5,
                "amount": 40,
            },
            "metadata": {
                "hyperion_checkout_id": str(checkout.id),
                "secret": "secret",
            },
        },
    )

    assert response.status_code == 204
    mocked_callback.assert_called_once()
    mocked_hyperion_security_logger.assert_called_with(
        f"Payment: call to module {TEST_MODULE_ROOT} payment callback for checkout (hyperion_checkout_id: {checkout.id}, HelloAsso checkout_id: {checkout.id}) failed with an error Test error",
    )
