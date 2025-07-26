import uuid
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from helloasso_python.models.hello_asso_api_v5_models_carts_init_checkout_body import (
    HelloAssoApiV5ModelsCartsInitCheckoutBody,
)
from helloasso_python.models.hello_asso_api_v5_models_carts_init_checkout_response import (
    HelloAssoApiV5ModelsCartsInitCheckoutResponse,
)
from pytest_mock import MockerFixture
from requests import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment import cruds_payment, models_payment, schemas_payment
from app.core.payment.payment_tool import PaymentTool
from app.core.payment.types_payment import HelloAssoConfig, HelloAssoConfigName
from app.core.schools import schemas_schools
from app.core.users import schemas_users
from app.types.module import Module
from tests.commons import (
    MockedPaymentTool,
    TestingSessionLocal,
    add_object_to_db,
    create_user_with_groups,
)

if TYPE_CHECKING:
    from app.core.utils.config import Settings

checkout_with_existing_checkout_payment: models_payment.Checkout
existing_checkout_payment: models_payment.CheckoutPayment
checkout: models_payment.Checkout

user_schema: schemas_users.CoreUser

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
        secret="secret",
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
        secret="secret",
    )
    await add_object_to_db(checkout)

    global user_schema
    user = await create_user_with_groups(
        groups=[],
    )
    school = schemas_schools.CoreSchool(
        id=user.school.id,
        name=user.school.name,
        email_regex=user.school.email_regex,
    )
    user_dict = user.__dict__
    user_dict.pop("school")

    user_schema = schemas_users.CoreUser(**user_dict, school=school)


# Test endpoints #


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


def test_webhook_payment_with_invalid_helloasso_secret(
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
    checkout_payment: schemas_payment.CheckoutPayment,
    db: AsyncSession,
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
        factory=None,
    )
    mocker.patch(
        "app.core.payment.endpoints_payment.all_modules",
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
        factory=None,
    )
    mocker.patch(
        "app.core.payment.endpoints_payment.all_modules",
        [test_module],
    )

    mocked_hyperion_security_logger = mocker.patch(
        "app.core.payment.endpoints_payment.hyperion_error_logger.exception",
    )

    response = client.post(
        "/payment/helloasso/webhook",
        json={
            "eventType": "Payment",
            "data": {
                "id": 6,
                "amount": 40,
            },
            "metadata": {
                "hyperion_checkout_id": str(checkout.id),
                "secret": "secret",
            },
        },
    )

    assert response.status_code == 204, response.text
    mocked_callback.assert_called_once()
    mocked_hyperion_security_logger.assert_called_with(
        f"Payment: call to module {TEST_MODULE_ROOT} payment callback for checkout (hyperion_checkout_id: {checkout.id}, HelloAsso checkout_id: {checkout.id}) failed",
    )


# Test Payment tool #


async def test_payment_tool_get_checkout(
    client: TestClient,
):
    payment_tool = MockedPaymentTool()

    async with TestingSessionLocal() as db:
        # Get existing checkout
        existing_checkout = await payment_tool.get_checkout(
            checkout_id=checkout_with_existing_checkout_payment.id,
            db=db,
        )
        assert existing_checkout is not None
        assert existing_checkout.id == checkout_with_existing_checkout_payment.id

        # Get non existing checkout
        unexisting_checkout = await payment_tool.get_checkout(
            checkout_id=uuid.uuid4(),
            db=db,
        )
        assert unexisting_checkout is None


async def test_payment_tool_init_checkout(
    mocker: MockerFixture,
):
    redirect_url = "https://example.com"
    # We create a mocked settings object with the required HelloAsso API credentials
    settings: Settings = mocker.MagicMock()
    settings.HELLOASSO_API_BASE = "https://example.com"
    settings.HELLOASSO_CONFIGURATIONS = {
        HelloAssoConfigName.CDR: HelloAssoConfig(
            helloasso_client_id="clientid",
            helloasso_client_secret="secret",
            helloasso_slug="test",
            redirect_url=redirect_url,
        ),
    }
    payment_tool = PaymentTool(
        config=settings.HELLOASSO_CONFIGURATIONS[HelloAssoConfigName.CDR],
        helloasso_api_base=settings.HELLOASSO_API_BASE,
    )

    mocker.patch.object(
        payment_tool,
        "get_access_token",
        return_value="access_token",
    )

    # We mock the whole CheckoutAPI to avoid making real API calls
    # and prevent the class initialization from failing to authenticate
    # We mock the init checkout method to return a mocked response
    mock_checkout_api = mocker.MagicMock()
    mock_checkout_api.organizations_organization_slug_checkout_intents_post.return_value = HelloAssoApiV5ModelsCartsInitCheckoutResponse(
        id=7,
        redirect_url=redirect_url,
    )
    mocker.patch(
        "app.core.payment.payment_tool.CheckoutApi",
        return_value=mock_checkout_api,
    )

    async with TestingSessionLocal() as db:
        returned_checkout = await payment_tool.init_checkout(
            module="testtool",
            checkout_amount=100,
            checkout_name="test",
            redirection_uri="redirect",
            db=db,
            payer_user=user_schema,
        )

        assert returned_checkout.payment_url == redirect_url

        # We want to check that the checkout was created in the database
        created_checkout = await payment_tool.get_checkout(
            checkout_id=returned_checkout.id,
            db=db,
        )
        assert created_checkout is not None


async def test_payment_tool_init_checkout_with_one_failure(
    mocker: MockerFixture,
):
    """
    When HelloAsso init_checkout fail a first time, we want to retry a second time without payers infos.
    """
    redirect_url = "https://example.com"
    # We create a mocked settings object with the required HelloAsso API credentials
    settings: Settings = mocker.MagicMock()
    settings.HELLOASSO_API_BASE = "https://example.com"
    settings.HELLOASSO_CONFIGURATIONS = {
        HelloAssoConfigName.CDR: HelloAssoConfig(
            helloasso_client_id="clientid",
            helloasso_client_secret="secret",
            helloasso_slug="test",
            redirect_url=redirect_url,
        ),
    }

    payment_tool = PaymentTool(
        config=settings.HELLOASSO_CONFIGURATIONS[HelloAssoConfigName.CDR],
        helloasso_api_base=settings.HELLOASSO_API_BASE,
    )

    # We create a side effect for the `init_a_checkout` method that will raise an error the first time
    # init_checkout is called with a payer, and return a mocked response the second time
    def init_a_checkout_side_effect(
        helloasso_slug: str,
        init_checkout_body: HelloAssoApiV5ModelsCartsInitCheckoutBody,
    ):
        if init_checkout_body.payer is not None:
            r = Response()
            r.status_code = 400
            raise Exception  # noqa: TRY002
        return HelloAssoApiV5ModelsCartsInitCheckoutResponse(
            id=7,
            redirect_url=redirect_url,
        )

    mocker.patch.object(
        payment_tool,
        "get_access_token",
        return_value="access_token",
    )

    # We mock the whole HelloAssoAPIWrapper to avoid making real API calls
    # and prevent the class initialization from failing to authenticate
    # We mock the init checkout method to return a mocked response
    mock_checkout_api = mocker.MagicMock()
    mock_checkout_api.organizations_organization_slug_checkout_intents_post.side_effect = init_a_checkout_side_effect
    mocker.patch(
        "app.core.payment.payment_tool.CheckoutApi",
        return_value=mock_checkout_api,
    )

    async with TestingSessionLocal() as db:
        returned_checkout = await payment_tool.init_checkout(
            module="testtool",
            checkout_amount=100,
            checkout_name="test",
            redirection_uri="redirect",
            db=db,
            payer_user=user_schema,
        )

        assert returned_checkout.payment_url == redirect_url

        # We want to check that the checkout was created in the database
        created_checkout = await payment_tool.get_checkout(
            checkout_id=returned_checkout.id,
            db=db,
        )
        assert created_checkout is not None


async def test_payment_tool_init_checkout_fail(
    mocker: MockerFixture,
    client: TestClient,
) -> None:
    mocked_hyperion_security_logger = mocker.patch(
        "app.core.payment.endpoints_payment.hyperion_error_logger.error",
    )

    redirect_url = "https://example.com"
    # We create a mocked settings object with the required HelloAsso API credentials
    settings: Settings = mocker.MagicMock()
    settings.HELLOASSO_API_BASE = "https://example.com"
    settings.HELLOASSO_CONFIGURATIONS = {
        HelloAssoConfigName.CDR: HelloAssoConfig(
            helloasso_client_id="clientid",
            helloasso_client_secret="secret",
            helloasso_slug="test",
            redirect_url=redirect_url,
        ),
    }

    payment_tool = PaymentTool(
        config=settings.HELLOASSO_CONFIGURATIONS[HelloAssoConfigName.CDR],
        helloasso_api_base=settings.HELLOASSO_API_BASE,
    )

    mocker.patch.object(
        payment_tool,
        "get_access_token",
        return_value="access_token",
    )

    # We mock the whole HelloAssoAPIWrapper to avoid making real API calls
    # and prevent the class initialization from failing to authenticate
    # We mock the init checkout method to raise an error
    mock_checkout_api = mocker.MagicMock()
    mock_checkout_api.organizations_organization_slug_checkout_intents_post.side_effect = ValueError(
        "Mocked Exception",
    )

    mocker.patch(
        "app.core.payment.payment_tool.CheckoutApi",
        return_value=mock_checkout_api,
    )

    with pytest.raises(ValueError, match="Mocked Exception"):
        async with TestingSessionLocal() as db:
            await payment_tool.init_checkout(
                module="testtool",
                checkout_amount=100,
                checkout_name="test",
                redirection_uri="redirect",
                db=db,
                payer_user=user_schema,
            )

    mocked_hyperion_security_logger.assert_called()
