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
    res = await request.json()
    print(res)
    if content.eventType == ApiNotificationType.Order:
        pass
    if content.eventType == ApiNotificationType.Payment:
        # We may receive the webhook multiple times, we only want to save a CheckoutPayment
        # in the database the first time
        checkout_payment_model = (
            cruds_payment.get_checkout_payment_by_hello_asso_payment_id(
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
