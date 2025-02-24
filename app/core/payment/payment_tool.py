import logging
import uuid

from helloasso_api_wrapper import HelloAssoAPIWrapper
from helloasso_api_wrapper.exceptions import ApiV5BadRequest
from helloasso_api_wrapper.models.carts import (
    CheckoutPayer,
    InitCheckoutBody,
    InitCheckoutResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment import cruds_payment, models_payment, schemas_payment
from app.core.users import schemas_users
from app.core.utils import security
from app.core.utils.config import Settings
from app.types.exceptions import PaymentToolCredentialsNotSetException

hyperion_error_logger = logging.getLogger("hyperion.error")


class PaymentTool:
    hello_asso: HelloAssoAPIWrapper | None

    def __init__(self, settings: Settings):
        if (
            settings.HELLOASSO_API_BASE
            and settings.HELLOASSO_CLIENT_ID
            and settings.HELLOASSO_CLIENT_SECRET
        ):
            self.hello_asso = HelloAssoAPIWrapper(
                api_base=settings.HELLOASSO_API_BASE,
                client_id=settings.HELLOASSO_CLIENT_ID,
                client_secret=settings.HELLOASSO_CLIENT_SECRET,
                timeout=60,
            )
        else:
            hyperion_error_logger.warning(
                "HelloAsso API credentials are not set, payment won't be available",
            )
            self.hello_asso = None

    def is_payment_available(self) -> bool:
        """
        If the API credentials are not set, payment won't be available. If credentials are set, this doesn't ensure that they are valid.

        You should always call this method before trying to init a checkout
        If payment is not available, you usually should raise an HTTP Exception explaining that payment is disabled because the API credentials are not configured in settings.
        """
        return self.hello_asso is not None

    async def init_checkout(
        self,
        module: str,
        helloasso_slug: str,
        checkout_amount: int,
        checkout_name: str,
        redirection_uri: str,
        db: AsyncSession,
        payer_user: schemas_users.CoreUser | None = None,
    ) -> schemas_payment.Checkout:
        """
        Init an HelloAsso checkout

        Params:
            helloasso_slug: the slug of the HelloAsso organization
            checkout_amount: amount in centimes
            checkout_name: name to display for the payment
            redirection_uri: redirect the user after the payment.
                The status of the payment will be included in a query param but can not be thrusted
                This must be an https url
            payer_user: prefill some information about the payer

        Return:
            id: id of the Hyperion's Checkout, you should save it to be able to get information about the checkout
            payment_url: you need to redirect the user to this payment page

        This method use HelloAsso API. It may raise exceptions if HA checkout initialization fails.
        Exceptions can be imported from `helloasso_api_wrapper.exceptions`
        """
        if not self.hello_asso:
            raise PaymentToolCredentialsNotSetException

        # We want to ensure that any error is logged, even if modules tries to try/except this method
        # Thus we catch any exception and log it, then reraise it
        try:
            payer: CheckoutPayer | None = None
            if payer_user:
                payer = CheckoutPayer(
                    firstName=payer_user.firstname,
                    lastName=payer_user.name,
                    email=payer_user.email,
                    dateOfBirth=payer_user.birthday,
                )

            checkout_model_id = uuid.uuid4()
            secret = security.generate_token(nbytes=12)

            init_checkout_body = InitCheckoutBody(
                totalAmount=checkout_amount,
                initialAmount=checkout_amount,
                itemName=checkout_name,
                backUrl=redirection_uri,
                errorUrl=redirection_uri,
                returnUrl=redirection_uri,
                containsDonation=False,
                payer=payer,
                metadata=schemas_payment.HelloAssoCheckoutMetadata(
                    secret=secret,
                    hyperion_checkout_id=str(checkout_model_id),
                ).model_dump(),
            )

            # TODO: if payment fail, we can retry
            # then try without the payer infos
            response: InitCheckoutResponse
            try:
                response = self.hello_asso.checkout_intents_management.init_a_checkout(
                    helloasso_slug,
                    init_checkout_body,
                )
            except ApiV5BadRequest:
                # We know that HelloAsso may refuse some payer infos, like using the firstname "test"
                # Even when prefilling the payer infos,the user will be able to edit them on the payment page,
                # so we can safely retry without the payer infos
                hyperion_error_logger.exception(
                    f"Payment: failed to init a checkout with HA for module {module} and name {checkout_name}. Retrying without payer infos",
                )

                init_checkout_body.payer = None
                response = self.hello_asso.checkout_intents_management.init_a_checkout(
                    helloasso_slug,
                    init_checkout_body,
                )

            checkout_model = models_payment.Checkout(
                id=checkout_model_id,
                module=module,
                name=checkout_name,
                amount=checkout_amount,
                hello_asso_checkout_id=response.id,
                secret=secret,
            )

            await cruds_payment.create_checkout(db=db, checkout=checkout_model)

            return schemas_payment.Checkout(
                id=checkout_model_id,
                payment_url=response.redirectUrl,
            )
        except Exception:
            hyperion_error_logger.exception(
                f"Payment: failed to init a checkout with HA for module {module} and name {checkout_name}",
            )
            raise

    async def get_checkout(
        self,
        checkout_id: uuid.UUID,
        db: AsyncSession,
    ) -> schemas_payment.CheckoutComplete | None:
        checkout_model = await cruds_payment.get_checkout_by_id(
            checkout_id=checkout_id,
            db=db,
        )
        if checkout_model is None:
            return None

        checkout_dict = checkout_model.__dict__
        checkout_dict["payments"] = [
            schemas_payment.CheckoutPayment(**payment.__dict__)
            for payment in checkout_dict["payments"]
        ]
        return schemas_payment.CheckoutComplete(**checkout_dict)
