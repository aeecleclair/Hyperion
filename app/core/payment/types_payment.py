from datetime import datetime
from enum import Enum
from typing import Any, Literal

from helloasso_python.models.hello_asso_api_v5_models_api_notifications_api_notification_type import (
    HelloAssoApiV5ModelsApiNotificationsApiNotificationType,
)
from helloasso_python.models.hello_asso_api_v5_models_carts_checkout_payer import (
    HelloAssoApiV5ModelsCartsCheckoutPayer,
)
from helloasso_python.models.hello_asso_api_v5_models_common_meta_model import (
    HelloAssoApiV5ModelsCommonMetaModel,
)
from helloasso_python.models.hello_asso_api_v5_models_enums_payment_means import (
    HelloAssoApiV5ModelsEnumsPaymentMeans,
)
from helloasso_python.models.hello_asso_api_v5_models_enums_payment_state import (
    HelloAssoApiV5ModelsEnumsPaymentState,
)
from helloasso_python.models.hello_asso_api_v5_models_enums_payment_type import (
    HelloAssoApiV5ModelsEnumsPaymentType,
)
from helloasso_python.models.hello_asso_api_v5_models_statistics_refund_operation_light_model import (
    HelloAssoApiV5ModelsStatisticsRefundOperationLightModel,
)
from pydantic import BaseModel

"""
We are forced to hardcode the following models because they are not available in the helloasso-python package.
According to the swagger we should use a model called `Models.Orders.PaymentDetail` which doesn't seem to exist


The closest model in term of field is `HelloAssoApiV5ModelsStatisticsPaymentDetail`
which does not contain the field `date` expected in the documentation example: https://dev.helloasso.com/docs/notification-exemple#paiement-autoris%C3%A9-sur-un-checkout
"""


class HelloAssoConfigName(Enum):
    CDR = "CDR"
    RAID = "RAID"
    MYECLPAY = "MYECLPAY"


class HelloAssoConfig(BaseModel):
    name: HelloAssoConfigName
    helloasso_client_id: str
    helloasso_client_secret: str
    helloasso_slug: str
    redirection_uri: str | None = None


class PaymentDetail(BaseModel):
    payer: HelloAssoApiV5ModelsCartsCheckoutPayer | None = None

    id: int
    amount: int
    amountTip: int | None = None
    date: datetime | None = None
    installmentNumber: int | None = None
    state: HelloAssoApiV5ModelsEnumsPaymentState | None = None
    type: HelloAssoApiV5ModelsEnumsPaymentType | None = None
    meta: HelloAssoApiV5ModelsCommonMetaModel | None = None
    paymentOffLineMean: HelloAssoApiV5ModelsEnumsPaymentMeans | None = None
    refundOperations: (
        list[HelloAssoApiV5ModelsStatisticsRefundOperationLightModel] | None
    ) = None


class OrganizationNotificationResultData(BaseModel):
    old_slug_organization: str
    new_slug_organization: str


class OrganizationNotificationResultContent(BaseModel):
    eventType: Literal[
        HelloAssoApiV5ModelsApiNotificationsApiNotificationType.ORGANIZATION
    ]
    data: OrganizationNotificationResultData
    metadata: None = None  # not sure


class OrderNotificationResultContent(BaseModel):
    """
    metadata should contain the metadata sent while creating the checkout intent in `InitCheckoutBody`
    """

    eventType: Literal[HelloAssoApiV5ModelsApiNotificationsApiNotificationType.ORDER]
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None


class PayementNotificationResultContent(BaseModel):
    """
    metadata should contain the metadata sent while creating the checkout intent in `InitCheckoutBody`
    """

    eventType: Literal[HelloAssoApiV5ModelsApiNotificationsApiNotificationType.PAYMENT]
    data: PaymentDetail
    metadata: dict[str, Any] | None = None


class FormNotificationResultContent(BaseModel):
    eventType: Literal[HelloAssoApiV5ModelsApiNotificationsApiNotificationType.FORM]
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None  # not sure


NotificationResultContent = (
    OrganizationNotificationResultContent
    | OrderNotificationResultContent
    | PayementNotificationResultContent
    | FormNotificationResultContent
)
"""
When a new content is available, HelloAsso will call the notification URL callback with the corresponding data in the body.
"""
