import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from helloasso_api_wrapper.models.api_notifications import (
    ApiNotificationType,
    NotificationResultContent,
)
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment import cruds_payment, models_payment
from app.dependencies import get_db

router = APIRouter(tags=["Payments"])

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.post(
    "/payment/helloasso/webhook",
    status_code=204,
)
async def webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        # We validate the body of the request ourself
        # to prevent FastAPI from returning a 422 error to HelloAsso
        # without logging the error
        content = NotificationResultContent.model_validate(await request.json())
    except ValidationError:
        hyperion_error_logger.error(
            f"Payment: could not validate the webhook body: {await request.body()}",
        )
        raise HTTPException(
            status_code=400,
            detail="Could not validate the webhook body",
        )
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
