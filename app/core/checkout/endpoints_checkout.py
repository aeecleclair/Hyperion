import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from helloasso_python.models.hello_asso_api_v5_models_api_notifications_api_notification_type import (
    HelloAssoApiV5ModelsApiNotificationsApiNotificationType,
)
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.checkout import cruds_checkout, models_checkout, schemas_checkout
from app.core.checkout.types_checkout import (
    NotificationResultContent,
)
from app.dependencies import get_db
from app.module import all_modules
from app.types.module import CoreModule

router = APIRouter(tags=["Payments"])

core_module = CoreModule(
    root="payment",
    tag="Payments",
    router=router,
    factory=None,
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
        type_adapter: TypeAdapter[NotificationResultContent] = TypeAdapter(
            NotificationResultContent,
        )
        content = type_adapter.validate_python(
            await request.json(),
        )
        if content.metadata:
            checkout_metadata = (
                schemas_checkout.HelloAssoCheckoutMetadata.model_validate(
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
    if (
        content.eventType
        == HelloAssoApiV5ModelsApiNotificationsApiNotificationType.ORDER
    ):
        pass
    if (
        content.eventType
        == HelloAssoApiV5ModelsApiNotificationsApiNotificationType.PAYMENT
    ):
        # We may receive the webhook multiple times, we only want to save a CheckoutPayment
        # in the database the first time
        existing_checkout_payment_model = (
            await cruds_checkout.get_checkout_payment_by_hello_asso_payment_id(
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

        checkout = await cruds_checkout.get_checkout_by_id(
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

        checkout_payment_model = models_checkout.CheckoutPayment(
            id=uuid.uuid4(),
            checkout_id=checkout.id,
            paid_amount=content.data.amount,
            tip_amount=content.data.amountTip,
            hello_asso_payment_id=content.data.id,
        )
        await cruds_checkout.create_checkout_payment(
            checkout_payment=checkout_payment_model,
            db=db,
        )

        hyperion_error_logger.info(
            f"Payment: checkout payment added to db for checkout (hyperion_checkout_id: {checkout_metadata.hyperion_checkout_id}, HelloAsso checkout_id: {checkout.id})",
        )

        # If a callback is defined for the module, we want to call it
        try:
            for module in all_modules:
                if module.root == checkout.module:
                    if module.checkout_callback is None:
                        hyperion_error_logger.info(
                            f"Payment: calling module {checkout.module} payment callback",
                        )
                        return
                    hyperion_error_logger.info(
                        f"Payment: calling module {checkout.module} payment callback",
                    )
                    checkout_payment_schema = schemas_checkout.CheckoutPayment(
                        id=checkout_payment_model.id,
                        paid_amount=checkout_payment_model.paid_amount,
                        checkout_id=checkout_payment_model.checkout_id,
                    )
                    await module.checkout_callback(checkout_payment_schema, db)
                    hyperion_error_logger.info(
                        f"Payment: call to module {checkout.module} payment callback for checkout (hyperion_checkout_id: {checkout_metadata.hyperion_checkout_id}, HelloAsso checkout_id: {checkout.id}) succeeded",
                    )
                    return

            hyperion_error_logger.info(
                f"Payment: callback for checkout (hyperion_checkout_id: {checkout_metadata.hyperion_checkout_id}, HelloAsso checkout_id: {checkout.id}) was not called for module {checkout.module}",
            )
        except Exception:
            hyperion_error_logger.exception(
                f"Payment: call to module {checkout.module} payment callback for checkout (hyperion_checkout_id: {checkout_metadata.hyperion_checkout_id}, HelloAsso checkout_id: {checkout.id}) failed",
            )
