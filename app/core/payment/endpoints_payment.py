import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from helloasso_api_wrapper import HelloAssoAPIWrapper
from helloasso_api_wrapper.models.api_notifications import (
    ApiNotificationType,
    NotificationResultContent,
)
from helloasso_api_wrapper.models.carts import CheckoutPayer, InitCheckoutBody
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.payment import cruds_payment, models_payment
from app.dependencies import get_db, get_settings

router = APIRouter(tags=["Payments"])


@router.post(
    "/payment/helloasso/webhook",
    status_code=204,
)
async def webhook(
    request: Request,
    content: NotificationResultContent,
    db: AsyncSession = Depends(get_db),
):
    # TODO: don't return a 422
    # res = await request.json()
    # print(res)
    if content.eventType == ApiNotificationType.Order:
        pass
    if content.eventType == ApiNotificationType.Payment:
        # We may receive the webhook multiple times, we only want to save a CheckoutPayment
        # in the database the first time
        checkout_payment_model = (
            await cruds_payment.get_checkout_payment_by_hello_asso_payment_id(
                hello_asso_payment_id=content.data.id,
                db=db,
            )
        )
        if checkout_payment_model is None:
            checkout_payment_model = models_payment.CheckoutPayment(
                id=uuid.uuid4(),
                paid_amount=content.data.amount,
                hello_asso_payment_id=content.data.id,
            )


@router.get(
    "/payement/redirect/{result}",
    response_class=HTMLResponse,
)
async def result(
    result: str,
):
    print(f"Returned with result {result}")
    return """
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
            <h1>Look ma! HTML!</h1>
        </body>
    </html>
    """


@router.get(
    "/payment",
)
async def payment(
    settings: Settings = Depends(get_settings),
):
    hello_asso = HelloAssoAPIWrapper(
        api_base=settings.HELLOASSO_API_BASE,
        client_id=settings.HELLOASSO_CLIENT_ID,
        client_secret=settings.HELLOASSO_CLIENT_SECRET,
        timeout=60,
    )

    # res = hello_asso.users.get_my_organizations()

    slug = "aeecl"

    # res = hello_asso.organizations.get_organization_details(slug)

    url = "https://da96-2a04-cec0-f047-3a6f-3836-59a8-f3d5-142b.ngrok-free.app"

    init_checkout_body = InitCheckoutBody(
        totalAmount=13 * 100,
        initialAmount=13 * 100,
        itemName="Vente 4",
        backUrl=url + "/payment/redirect/back",
        errorUrl=url + "/payment/redirect/error",
        returnUrl=url + "/payment/redirect/return",
        containsDonation=False,
        payer=CheckoutPayer(firstName="Jho", lastName="eclair", email="a@a.fr"),
        metadata={"test": "testValue"},
    )

    res = hello_asso.checkout_intents_management.init_a_checkout(
        slug,
        init_checkout_body,
    )

    print(res)


@router.get(
    "/payment/retrieve",
)
async def payment_retrieve(
    settings: Settings = Depends(get_settings),
):
    hello_asso = HelloAssoAPIWrapper(
        api_base=settings.HELLOASSO_API_BASE,
        client_id=settings.HELLOASSO_CLIENT_ID,
        client_secret=settings.HELLOASSO_CLIENT_SECRET,
        timeout=60,
    )

    # res = hello_asso.users.get_my_organizations()

    slug = "aeecl"

    # res = hello_asso.organizations.get_organization_details(slug)

    idp = "21613"

    res = hello_asso.checkout_intents_management.retrieve_a_checkout_intent(slug, idp)

    print(res)
