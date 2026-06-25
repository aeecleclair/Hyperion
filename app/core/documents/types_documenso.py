"""
Schémas Pydantic pour les webhooks Documenso.
Couvre les événements : DOCUMENT_CREATED, DOCUMENT_COMPLETED, DOCUMENT_REJECTED,
TEMPLATE_CREATED, TEMPLATE_UPDATED, TEMPLATE_DELETED.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter


class DocumentStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class DocumentSource(StrEnum):
    DOCUMENT = "DOCUMENT"
    TEMPLATE = "TEMPLATE"


class DocumentVisibility(StrEnum):
    EVERYONE = "EVERYONE"
    MANAGER_AND_ABOVE = "MANAGER_AND_ABOVE"
    ADMIN = "ADMIN"


class SigningOrder(StrEnum):
    PARALLEL = "PARALLEL"
    SEQUENTIAL = "SEQUENTIAL"


class DistributionMethod(StrEnum):
    EMAIL = "EMAIL"
    NONE = "NONE"


class RecipientRole(StrEnum):
    SIGNER = "SIGNER"
    VIEWER = "VIEWER"
    APPROVER = "APPROVER"
    CC = "CC"


class ReadStatus(StrEnum):
    NOT_OPENED = "NOT_OPENED"
    OPENED = "OPENED"


class SigningStatus(StrEnum):
    NOT_SIGNED = "NOT_SIGNED"
    SIGNED = "SIGNED"
    REJECTED = "REJECTED"


class SendStatus(StrEnum):
    NOT_SENT = "NOT_SENT"
    SENT = "SENT"


class WebhookEvent(StrEnum):
    DOCUMENT_CREATED = "DOCUMENT_CREATED"
    DOCUMENT_COMPLETED = "DOCUMENT_COMPLETED"
    DOCUMENT_REJECTED = "DOCUMENT_REJECTED"
    TEMPLATE_CREATED = "TEMPLATE_CREATED"
    TEMPLATE_UPDATED = "TEMPLATE_UPDATED"
    TEMPLATE_DELETED = "TEMPLATE_DELETED"


# class AuthOptions(BaseModel):
#     access_auth: Any | None = Field(None, alias="accessAuth")
#     action_auth: Any | None = Field(None, alias="actionAuth")

#     model_config = {"populate_by_name": True}


# class DocumentMeta(BaseModel):
#     id: str
#     subject: str | None = None
#     message: str | None = None
#     timezone: str | None = None
#     password: str | None = None
#     date_format: str | None = Field(None, alias="dateFormat")
#     redirect_url: str | None = Field(None, alias="redirectUrl")
#     signing_order: SigningOrder | None = Field(None, alias="signingOrder")
#     allow_dictate_next_signer: bool | None = Field(
#         None,
#         alias="allowDictateNextSigner",
#     )
#     typed_signature_enabled: bool | None = Field(None, alias="typedSignatureEnabled")
#     upload_signature_enabled: bool | None = Field(
#         None,
#         alias="uploadSignatureEnabled",
#     )
#     draw_signature_enabled: bool | None = Field(None, alias="drawSignatureEnabled")
#     language: str | None = None
#     distribution_method: DistributionMethod | None = Field(
#         None,
#         alias="distributionMethod",
#     )
#     email_settings: Any | None = Field(None, alias="emailSettings")

#     model_config = {"populate_by_name": True}


class Recipient(BaseModel):
    id: int
    token: str
    # document_id: int | None = Field(None, alias="documentId")
    # template_id: int | None = Field(None, alias="templateId")
    # email: EmailStr
    # name: str
    # document_deleted_at: datetime | None = Field(None, alias="documentDeletedAt")
    # expires_at: datetime | None = Field(None, alias="expiresAt")
    # expiration_notified_at: datetime | None = Field(
    #     None,
    #     alias="expirationNotifiedAt",
    # )
    # signed_at: datetime | None = Field(None, alias="signedAt")
    # auth_options: AuthOptions | None = Field(None, alias="authOptions")
    # signing_order: int | None = Field(None, alias="signingOrder")
    # rejection_reason: str | None = Field(None, alias="rejectionReason")
    # role: RecipientRole
    # read_status: ReadStatus = Field(alias="readStatus")
    # signing_status: SigningStatus = Field(alias="signingStatus")
    # send_status: SendStatus = Field(alias="sendStatus")

    model_config = {"populate_by_name": True}


class BaseDocumensoPayload(BaseModel):
    """Champs communs à tous les payloads Documenso."""

    id: int
    external_id: str | None = Field(None, alias="externalId")
    title: str
    status: DocumentStatus
    team_id: int | None = Field(None, alias="teamId")
    source: DocumentSource
    recipients: list[Recipient] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    # user_id: int = Field(alias="userId")
    # auth_options: Any | None = Field(None, alias="authOptions")
    # form_values: Any | None = Field(None, alias="formValues")
    # visibility: DocumentVisibility
    # document_data_id: str = Field(alias="documentDataId")
    # completed_at: datetime | None = Field(None, alias="completedAt")
    # deleted_at: datetime | None = Field(None, alias="deletedAt")
    # template_id: int | None = Field(None, alias="templateId")
    # document_meta: DocumentMeta | None = Field(None, alias="documentMeta")

    model_config = {"populate_by_name": True}


class DocumentCreatedPayload(BaseDocumensoPayload):
    status: Literal[DocumentStatus.DRAFT] = DocumentStatus.DRAFT
    source: Literal[DocumentSource.DOCUMENT] = DocumentSource.DOCUMENT


class DocumentCompletedPayload(BaseDocumensoPayload):
    status: Literal[DocumentStatus.COMPLETED] = DocumentStatus.COMPLETED
    source: Literal[DocumentSource.DOCUMENT] = DocumentSource.DOCUMENT
    completed_at: datetime = Field(alias="completedAt")


class DocumentRejectedPayload(BaseDocumensoPayload):
    status: Literal[DocumentStatus.PENDING] = DocumentStatus.PENDING
    source: Literal[DocumentSource.DOCUMENT] = DocumentSource.DOCUMENT


class TemplateCreatedPayload(BaseDocumensoPayload):
    status: Literal[DocumentStatus.DRAFT] = DocumentStatus.DRAFT
    source: Literal[DocumentSource.TEMPLATE] = DocumentSource.TEMPLATE


class TemplateUpdatedPayload(BaseDocumensoPayload):
    status: Literal[DocumentStatus.DRAFT] = DocumentStatus.DRAFT
    source: Literal[DocumentSource.TEMPLATE] = DocumentSource.TEMPLATE


class TemplateDeletedPayload(BaseDocumensoPayload):
    status: Literal[DocumentStatus.DRAFT] = DocumentStatus.DRAFT
    source: Literal[DocumentSource.TEMPLATE] = DocumentSource.TEMPLATE


class DocumentCreatedWebhook(BaseModel):
    event: Literal[WebhookEvent.DOCUMENT_CREATED]
    payload: DocumentCreatedPayload
    created_at: datetime = Field(alias="createdAt")
    webhook_endpoint: str = Field(alias="webhookEndpoint")

    model_config = {"populate_by_name": True}


class DocumentCompletedWebhook(BaseModel):
    event: Literal[WebhookEvent.DOCUMENT_COMPLETED]
    payload: DocumentCompletedPayload
    created_at: datetime = Field(alias="createdAt")
    webhook_endpoint: str = Field(alias="webhookEndpoint")

    model_config = {"populate_by_name": True}


class DocumentRejectedWebhook(BaseModel):
    event: Literal[WebhookEvent.DOCUMENT_REJECTED]
    payload: DocumentRejectedPayload
    created_at: datetime = Field(alias="createdAt")
    webhook_endpoint: str = Field(alias="webhookEndpoint")

    model_config = {"populate_by_name": True}


class TemplateCreatedWebhook(BaseModel):
    event: Literal[WebhookEvent.TEMPLATE_CREATED]
    payload: TemplateCreatedPayload
    created_at: datetime = Field(alias="createdAt")
    webhook_endpoint: str = Field(alias="webhookEndpoint")

    model_config = {"populate_by_name": True}


class TemplateUpdatedWebhook(BaseModel):
    event: Literal[WebhookEvent.TEMPLATE_UPDATED]
    payload: TemplateUpdatedPayload
    created_at: datetime = Field(alias="createdAt")
    webhook_endpoint: str = Field(alias="webhookEndpoint")

    model_config = {"populate_by_name": True}


class TemplateDeletedWebhook(BaseModel):
    event: Literal[WebhookEvent.TEMPLATE_DELETED]
    payload: TemplateDeletedPayload
    created_at: datetime = Field(alias="createdAt")
    webhook_endpoint: str = Field(alias="webhookEndpoint")

    model_config = {"populate_by_name": True}


DocumensoWebhook = Annotated[
    DocumentCreatedWebhook
    | DocumentCompletedWebhook
    | DocumentRejectedWebhook
    | TemplateCreatedWebhook
    | TemplateUpdatedWebhook
    | TemplateDeletedWebhook,
    Field(discriminator="event"),
]


def parse_webhook(data: dict) -> DocumensoWebhook:
    adapter: TypeAdapter[DocumensoWebhook] = TypeAdapter(DocumensoWebhook)
    return adapter.validate_python(data)
