from sqlalchemy.ext.asyncio import AsyncSession

from app.core.checkout.payment_tool import CheckoutTool
from app.core.mypayment import (
    schemas_mypayment,
    utils_mypayment,
)
from app.core.mypayment.types_mypayment import (
    RequestType,
)
from app.core.users import schemas_users
from app.core.utils.config import Settings
from app.utils.communication.notifications import NotificationTool


class MyPaymentTool:
    """
    Utility class to interact with MyPayment core module

    The dependency `get_mypayment_tool` should be used to get an instance of this class, which will ensure that all dependencies are properly injected.
    """

    def __init__(
        self,
        db: AsyncSession,
        checkout_tool: CheckoutTool,
        notification_tool: NotificationTool,
        settings: Settings,
    ):
        self.db = db
        self.checkout_tool = checkout_tool
        self.notification_tool = notification_tool
        self.settings = settings

    async def request_payment(
        self,
        request_type: RequestType,
        payment_info: schemas_mypayment.PaymentInfo,
        user: schemas_users.CoreUser,
    ) -> schemas_mypayment.PaymentRequestInfo:
        """
        Initiate a payment request. This request can be either:
         - a REQUEST_TRANSFER: a checkout will be instantiated, and be credited directly to the store wallet.
            In this case, a `checkout_url` url will be returned, the user should be redirected to this url to complete the checkout.
         - a REQUEST_TRANSACTION: when accepted by the user, a transaction will be created between the user wallet and the store wallet.
            The user should be redirected to mypayment module, to be asked to accept or refuse the transaction request.

        The request is valid until `end_date`

        The `CheckoutTool` must be a *MyPayment* checkout tool

        Use `get_mypayment_tool` dependency to get an instance of `MyPaymentTool`, which will ensure that all dependencies are properly injected.

        When the request is confirmed (checkout validated or transaction accepted), a callback will be called, with the following signature:
        ```python
        async def mypayment_callback(object_id: UUID, db: AsyncSession)
        ```
        """
        return await utils_mypayment.request_payment(
            request_type=request_type,
            payment_info=payment_info,
            user=user,
            db=self.db,
            checkout_tool=self.checkout_tool,
            notification_tool=self.notification_tool,
            settings=self.settings,
        )
