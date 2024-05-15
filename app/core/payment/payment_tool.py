import uuid

from helloasso_api_wrapper import HelloAssoAPIWrapper
from helloasso_api_wrapper.models.carts import CheckoutPayer, InitCheckoutBody
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.models_core import CoreUser
from app.core.payment import cruds_payment, models_payment, schemas_payment


class PaymentTool:
    def __init__(self, settings: Settings):
        self.hello_asso = HelloAssoAPIWrapper(
            api_base=settings.HELLOASSO_API_BASE,
            client_id=settings.HELLOASSO_CLIENT_ID,
            client_secret=settings.HELLOASSO_CLIENT_SECRET,
            timeout=60,
        )

    async def init_checkout(
        self,
        module: str,
        helloasso_slug: str,
        checkout_amount: int,
        checkout_name: str,
        redirection_uri: str,
        payer_user: CoreUser | None,
        db: AsyncSession,
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
        """
        payer: CheckoutPayer | None = None
        if payer_user:
            payer = CheckoutPayer(
                firstName=payer_user.firstname,
                lastName=payer_user.name,
                email=payer_user.email,
                dateOfBirth=payer_user.birthday,
            )
        init_checkout_body = InitCheckoutBody(
            totalAmount=checkout_amount,
            initialAmount=checkout_amount,
            itemName=checkout_name,
            backUrl=redirection_uri,
            errorUrl=redirection_uri,
            returnUrl=redirection_uri,
            containsDonation=False,
            payer=payer,
        )

        response = self.hello_asso.checkout_intents_management.init_a_checkout(
            helloasso_slug,
            init_checkout_body,
        )

        checkout_model_id = uuid.uuid4()

        checkout_model = models_payment.Checkout(
            id=checkout_model_id,
            module=module,
            name=checkout_name,
            amount=checkout_amount,
            paid_amount=0,
            hello_asso_checkout_id=response.id,
            hello_asso_order_id=None,
        )

        await cruds_payment.create_checkout(db=db, checkout=checkout_model)

        return schemas_payment.Checkout(
            id=checkout_model_id,
            payment_url=response.redirectUrl,
        )

    def get_checkout(
        self,
        checkout_id: uuid.UUID,
        db: AsyncSession,
    ) -> schemas_payment.CheckoutComplete:
        checkout_model = cruds_payment.get_checkout_by_id(
            checkout_id=checkout_id,
            db=db,
        )
        return schemas_payment.CheckoutComplete.model_validate(checkout_model)
