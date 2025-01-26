import logging
import uuid
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request
from helloasso_api_wrapper.models.api_notifications import (
    ApiNotificationType,
    NotificationResultContent,
)
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment import cruds_payment, models_payment, schemas_payment
from app.dependencies import get_db
from app.modules.module_list import module_list
from app.types.module import CoreModule

router = APIRouter(tags=["Payments"])

core_module = CoreModule(
    root="payment",
    tag="Payments",
    router=router,
)

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
        type_adapter = TypeAdapter(NotificationResultContent)
        validated_content = type_adapter.validate_python(
            await request.json(),
        )
        content = cast(NotificationResultContent, validated_content)
        if content.metadata:
            checkout_metadata = (
                schemas_payment.HelloAssoCheckoutMetadata.model_validate(
                    content.metadata,
                )
            )
        else:
            checkout_metadata = None
    except ValidationError:
        hyperion_error_logger.exception(
            f"Payment: could not validate the webhook body: {await request.json()}, failed",
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
        existing_checkout_payment_model = (
            await cruds_payment.get_checkout_payment_by_hello_asso_payment_id(
                hello_asso_payment_id=content.data.id,
                db=db,
            )
        )
        if existing_checkout_payment_model is not None:
            hyperion_error_logger.debug(
                f"Payment: ignoring webhook call for helloasso checkout payment id {content.data.id} as it already exists in the database",
            )
            return

        # If no metadata are included, this should not be a checkout we initiated
        if not checkout_metadata:
            hyperion_error_logger.info(
                "Payment: missing checkout_metadata",
            )
            return

        checkout = await cruds_payment.get_checkout_by_id(
            checkout_id=uuid.UUID(checkout_metadata.hyperion_checkout_id),
            db=db,
        )
        # If a metadata with a checkout was present in the request but we can not find the checkout,
        # we should raise an error
        if not checkout:
            hyperion_error_logger.error(
                f"Payment: could not find checkout (hyperion_checkout_id: {checkout_metadata.hyperion_checkout_id}) in database for payment HelloAsso payment_id: {content.data.id}",
            )
            raise HTTPException(
                status_code=400,
                detail=f"Could not find checkout {checkout_metadata.hyperion_checkout_id} in database",
            )

        if checkout.secret != checkout_metadata.secret:
            hyperion_error_logger.error(
                f"Payment: secret mismatch for checkout (hyperion_checkout_id: {checkout_metadata.hyperion_checkout_id}, HelloAsso checkout_id: {checkout.id})",
            )
            raise HTTPException(
                status_code=400,
                detail="Secret mismatch",
            )

        checkout_payment_model = models_payment.CheckoutPayment(
            id=uuid.uuid4(),
            checkout_id=checkout.id,
            paid_amount=content.data.amount,
            hello_asso_payment_id=content.data.id,
        )
        await cruds_payment.create_checkout_payment(
            checkout_payment=checkout_payment_model,
            db=db,
        )

        hyperion_error_logger.info(
            f"Payment: checkout payment added to db for checkout (hyperion_checkout_id: {checkout_metadata.hyperion_checkout_id}, HelloAsso checkout_id: {checkout.id})",
        )

        # If a callback is defined for the module, we want to call it
        try:
            for module in module_list:
                if module.root == checkout.module:
                    if module.payment_callback is not None:
                        hyperion_error_logger.info(
                            f"Payment: calling module {checkout.module} payment callback",
                        )
                        checkout_payment_schema = (
                            schemas_payment.CheckoutPayment.model_validate(
                                checkout_payment_model.__dict__,
                            )
                        )
                        await module.payment_callback(checkout_payment_schema, db)
                        hyperion_error_logger.info(
                            f"Payment: call to module {checkout.module} payment callback for checkout (hyperion_checkout_id: {checkout_metadata.hyperion_checkout_id}, HelloAsso checkout_id: {checkout.id}) succeeded",
                        )
                        return
        except Exception:
            hyperion_error_logger.exception(
                f"Payment: call to module {checkout.module} payment callback for checkout (hyperion_checkout_id: {checkout_metadata.hyperion_checkout_id}, HelloAsso checkout_id: {checkout.id}) failed",
            )
