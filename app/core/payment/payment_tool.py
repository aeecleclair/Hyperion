import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from authlib.integrations.requests_client import OAuth2Session
from helloasso_python.api.checkout_api import CheckoutApi
from helloasso_python.api.paiements_api import PaiementsApi
from helloasso_python.api_client import ApiClient
from helloasso_python.configuration import Configuration
from helloasso_python.models.hello_asso_api_v5_models_carts_checkout_payer import (
    HelloAssoApiV5ModelsCartsCheckoutPayer,
)
from helloasso_python.models.hello_asso_api_v5_models_carts_init_checkout_body import (
    HelloAssoApiV5ModelsCartsInitCheckoutBody,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment import cruds_payment, models_payment, schemas_payment
from app.core.payment.types_payment import HelloAssoConfig
from app.core.users import schemas_users
from app.core.utils import security
from app.types.exceptions import (
    MissingHelloAssoCheckoutIdError,
    PaymentToolCredentialsNotSetException,
)

if TYPE_CHECKING:
    from helloasso_python.models.hello_asso_api_v5_models_carts_init_checkout_response import (
        HelloAssoApiV5ModelsCartsInitCheckoutResponse,
    )

hyperion_error_logger = logging.getLogger("hyperion.error")


class PaymentTool:
    _access_token: str | None = None
    _refresh_token: str | None = None
    _access_token_expiry: int | None = None

    _auth_client: OAuth2Session
    _helloasso_api_base: str
    _helloasso_slug: str

    _redirection_uri: str | None = None

    def __init__(
        self,
        config: HelloAssoConfig,
        helloasso_api_base: str,
    ):
        self.name = config.name
        self._helloasso_api_base = helloasso_api_base
        self._auth_client = OAuth2Session(
            client_id=config.helloasso_client_id,
            client_secret=config.helloasso_client_secret,
            token_endpoint=f"https://{helloasso_api_base}/oauth2/token",
        )
        self._helloasso_slug = config.helloasso_slug
        self._redirection_uri = config.redirection_uri

        # else:
        #     hyperion_error_logger.warning(
        #         "HelloAsso API credentials are not set, payment won't be available",
        #     )

    def get_access_token(self) -> str:
        if not self._auth_client:
            raise PaymentToolCredentialsNotSetException
        # If the access token is not set, we get one
        if self._access_token is None:
            try:
                tokens = self._auth_client.fetch_token(grant_type="client_credentials")
            except Exception:
                hyperion_error_logger.exception(
                    "Payment: failed to get HelloAsso access token",
                )
                raise
            self._access_token = tokens["access_token"]
            self._refresh_token = tokens["refresh_token"]
            self._access_token_expiry = tokens["expires_at"]
        # If we have a token but it's expired, we need to refresh it
        # We refresh the token if it's expired or if it's about to expire in less than 3 minutes
        elif self._access_token_expiry is None or self._access_token_expiry < int(
            datetime.now(UTC).timestamp() - 3 * 60,
        ):
            # Token is expired, we need to refresh it
            try:
                tokens = self._auth_client.refresh_token(
                    refresh_token=self._refresh_token,
                )
                self._access_token = tokens["access_token"]
                self._refresh_token = tokens["refresh_token"]
                self._access_token_expiry = tokens["expires_at"]
                return self.get_access_token()
            except Exception:
                hyperion_error_logger.exception(
                    "Payment: failed to refresh HelloAsso access token, getting a new one",
                )
                self._access_token = None
                self._refresh_token = None
                self._access_token_expiry = None
                return self.get_access_token()

        return self._access_token

    def get_hello_asso_configuration(self) -> Configuration:
        """
        Get a valid access token and construct an HelloAsso API configuration object
        """
        access_token = self.get_access_token()
        if self._helloasso_api_base is None:
            raise PaymentToolCredentialsNotSetException
        return Configuration(
            host="https://" + self._helloasso_api_base + "/v5",
            access_token=access_token,
            retries=3,
        )

    def is_payment_available(self) -> bool:
        """
        If the API credentials are not set, payment won't be available. If credentials are set, this doesn't ensure that they are valid.

        You should always call this method before trying to init a checkout
        If payment is not available, you usually should raise an HTTP Exception explaining that payment is disabled because the API credentials are not configured in settings.
        """
        return (
            self._access_token is not None
            and self._access_token_expiry is not None
            and self._refresh_token is not None
        )

    async def init_checkout(
        self,
        module: str,
        checkout_amount: int,
        checkout_name: str,
        db: AsyncSession,
        payer_user: schemas_users.CoreUser | None = None,
        redirection_uri: str | None = None,
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
        Exceptions can be imported from `helloasso_python` package.
        """
        configuration = self.get_hello_asso_configuration()

        if not redirection_uri:
            redirection_uri = self._redirection_uri or ""

        # We want to ensure that any error is logged, even if modules tries to try/except this method
        # Thus we catch any exception and log it, then reraise it
        try:
            payer: HelloAssoApiV5ModelsCartsCheckoutPayer | None = None
            if payer_user:
                payer = HelloAssoApiV5ModelsCartsCheckoutPayer(
                    firstName=payer_user.firstname,
                    lastName=payer_user.name,
                    email=payer_user.email,
                    dateOfBirth=payer_user.birthday,
                )

            checkout_model_id = uuid.uuid4()
            secret = security.generate_token(nbytes=12)

            init_checkout_body = HelloAssoApiV5ModelsCartsInitCheckoutBody(
                total_amount=checkout_amount,
                initial_amount=checkout_amount,
                item_name=checkout_name,
                back_url=redirection_uri,
                error_url=redirection_uri,
                return_url=redirection_uri,
                contains_donation=False,
                payer=payer,
                metadata=schemas_payment.HelloAssoCheckoutMetadata(
                    secret=secret,
                    hyperion_checkout_id=str(checkout_model_id),
                ).model_dump(),
            )

            # TODO: if payment fail, we can retry
            # then try without the payer infos
            response: HelloAssoApiV5ModelsCartsInitCheckoutResponse
            with ApiClient(configuration) as api_client:
                checkout_api = CheckoutApi(api_client)
                try:
                    response = checkout_api.organizations_organization_slug_checkout_intents_post(
                        self._helloasso_slug,
                        init_checkout_body,
                    )
                except Exception:
                    # We know that HelloAsso may refuse some payer infos, like using the firstname "test"
                    # Even when prefilling the payer infos,the user will be able to edit them on the payment page,
                    # so we can safely retry without the payer infos
                    payer_user_name = ""
                    if payer_user:
                        payer_user_name = f"{payer_user.firstname} {payer_user.name}"
                    hyperion_error_logger.warning(
                        f"Payment: failed to init a checkout with HA for module {module} and name {checkout_name}. Retrying without payer {payer_user_name} infos",
                    )

                    init_checkout_body.payer = None
                    response = checkout_api.organizations_organization_slug_checkout_intents_post(
                        self._helloasso_slug,
                        init_checkout_body,
                    )

            if response.id is None:
                hyperion_error_logger.error(
                    f"Payment: failed to init a checkout with HA for module {module} and name {checkout_name}. No checkout id returned",
                )
                raise MissingHelloAssoCheckoutIdError()  # noqa: TRY301

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
                payment_url=response.redirect_url,
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

    async def refund_payment(
        self,
        checkout_id: uuid.UUID,
        hello_asso_payment_id: int,
        amount: int,
    ) -> None:
        """
        Refund a payment
        """
        configuration = self.get_hello_asso_configuration()

        with ApiClient(configuration) as api_client:
            paiements_api = PaiementsApi(api_client)
            try:
                paiements_api.payments_payment_id_refund_post(
                    payment_id=hello_asso_payment_id,
                    send_refund_mail=True,
                    amount=amount,
                )
            except Exception:
                hyperion_error_logger.exception(
                    f"Payment: failed to refund payment {hello_asso_payment_id} for checkout {checkout_id}",
                )
                raise
