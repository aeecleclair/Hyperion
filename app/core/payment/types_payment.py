from datetime import datetime
from enum import Enum
from typing import Any, Literal

from helloasso_python.models.hello_asso_api_v5_models_carts_checkout_payer import (
    HelloAssoApiV5ModelsCartsCheckoutPayer,
)
from pydantic import BaseModel


class MetaModel(BaseModel):
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class PaymentMeans(Enum):
    None_ = "None"
    Card = "Card"
    Check = "Check"
    Cash = "Cash"
    BankTransfer = "BankTransfer"
    Other = "Other"


class PaymentState(Enum):
    Pending = "Pending"
    Authorized = "Authorized"
    Refused = "Refused"
    Unknown = "Unknown"
    Registered = "Registered"
    Refunded = "Refunded"
    Refunding = "Refunding"
    Contested = "Contested"


class OperationState(Enum):
    UNKNOWN = "UNKNOWN"
    INIT = "INIT"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class PaymentType(Enum):
    Offline = "Offline"
    Credit = "Credit"
    Debit = "Debit"


class OrderAmountModel(BaseModel):
    total: int | None = None
    vat: int | None = None
    discount: int | None = None


class RefundOperationLightModel(BaseModel):
    id: int | None = None
    amount: int | None = None
    amountTip: int | None = None
    status: OperationState | None = None
    meta: MetaModel | None = None


class PaymentDetail(BaseModel):
    payer: HelloAssoApiV5ModelsCartsCheckoutPayer | None = None
    id: int
    amount: int
    amountTip: int | None = None
    date: datetime | None = None
    installmentNumber: int | None = None
    state: PaymentState | None = None
    type: PaymentType | None = None
    meta: MetaModel | None = None
    paymentOffLineMean: PaymentMeans | None = None
    refundOperations: list[RefundOperationLightModel] | None = None


class ApiNotificationType(str, Enum):
    Payment = "Payment"
    Order = "Order"
    Form = "Form"
    Organization = "Organization"


class PostApiUrlNotificationBody(BaseModel):
    url: str
    notificationType: ApiNotificationType | None = None


class ApiUrlNotificationModel(BaseModel):
    url: str | None = None
    apiNotificationType: ApiNotificationType | None = None


class OrganizationNotificationResultData(BaseModel):
    old_slug_organization: str
    new_slug_organization: str


class OrganizationNotificationResultContent(BaseModel):
    eventType: Literal[ApiNotificationType.Organization]
    data: OrganizationNotificationResultData
    metadata: None = None  # not sure


class OrderNotificationResultContent(BaseModel):
    """
    metadata should contain the metadata sent while creating the checkout intent in `InitCheckoutBody`
    """

    eventType: Literal[ApiNotificationType.Order]
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None


class PayementNotificationResultContent(BaseModel):
    """
    metadata should contain the metadata sent while creating the checkout intent in `InitCheckoutBody`
    """

    eventType: Literal[ApiNotificationType.Payment]
    data: PaymentDetail
    metadata: dict[str, Any] | None = None


class FormNotificationResultContent(BaseModel):
    eventType: Literal[ApiNotificationType.Form]
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
