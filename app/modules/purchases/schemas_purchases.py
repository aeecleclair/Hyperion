from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.ticket.schemas_ticket import GenerateTicketBase, GenerateTicketComplete
from app.core.users.schemas_users import CoreUserSimple
from app.modules.purchases.types_purchases import (
    DocumentSignatureType,
    PaymentType,
    PurchasesStatus,
)
from app.types.core_data import BaseCoreData
from app.types.floors_type import FloorsType
from app.types.websocket import WSMessageModel
from app.utils import validators


class DocumentBase(BaseModel):
    name: str


class DocumentComplete(DocumentBase):
    id: UUID
    seller_id: UUID

    model_config = ConfigDict(from_attributes=True)


class CurriculumBase(BaseModel):
    name: str


class CurriculumComplete(CurriculumBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class PurchasesUserPreview(CoreUserSimple):
    curriculum: CurriculumComplete | None = None


class PurchasesUser(PurchasesUserPreview):
    promo: int | None = None
    email: str
    birthday: date | None = None
    phone: str | None = None
    floor: FloorsType | None = None

    model_config = ConfigDict(from_attributes=True)


class PurchasesUserUpdate(BaseModel):
    promo: int | None = None
    nickname: str | None = None
    email: str | None = None
    birthday: date | None = None
    phone: str | None = None
    floor: FloorsType | None = None

    _normalize_nickname = field_validator("nickname")(
        validators.trailing_spaces_remover,
    )
    _format_phone = field_validator("phone")(
        validators.phone_formatter,
    )


class ProductVariantBase(BaseModel):
    name_fr: str
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    price: int
    enabled: bool
    unique: bool
    allowed_curriculum: list[UUID]
    related_membership_added_duration: timedelta | None = None
    needs_validation: bool


class ProductVariantComplete(BaseModel):
    id: UUID
    product_id: UUID
    name_fr: str
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    price: int
    enabled: bool
    unique: bool
    allowed_curriculum: list[CurriculumComplete] = []
    related_membership_added_duration: timedelta | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductVariantEdit(BaseModel):
    name_fr: str | None = None
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    price: int | None = None
    enabled: bool | None = None
    unique: bool | None = None
    allowed_curriculum: list[UUID] | None = None
    related_membership_added_duration: timedelta | None = None
    needs_validation: bool | None = None


class ProductBase(BaseModel):
    name_fr: str
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    available_online: bool
    related_membership_id: UUID | None = None
    tickets: list[GenerateTicketBase] = []
    product_constraints: list[UUID]
    document_constraints: list[UUID]


class ProductCompleteNoConstraint(BaseModel):
    name_fr: str
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    available_online: bool
    id: UUID
    seller_id: UUID
    variants: list[ProductVariantComplete] = []
    related_membership_id: UUID | None = None
    tickets: list[GenerateTicketComplete]

    model_config = ConfigDict(from_attributes=True)


class ProductComplete(BaseModel):
    name_fr: str
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    available_online: bool
    id: UUID
    seller_id: UUID
    variants: list[ProductVariantComplete] = []
    related_membership_id: UUID | None = None
    product_constraints: list[ProductCompleteNoConstraint] = []
    document_constraints: list[DocumentComplete] = []
    tickets: list[GenerateTicketComplete] = []

    model_config = ConfigDict(from_attributes=True)


class ProductEdit(BaseModel):
    name_fr: str | None = None
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    description: str | None = None
    available_online: bool | None = None
    related_membership_id: UUID | None = None
    product_constraints: list[UUID] | None = None
    document_constraints: list[UUID] | None = None


class SellerBase(BaseModel):
    name: str
    group_id: str
    order: int


class SellerComplete(SellerBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class SellerEdit(BaseModel):
    name: str | None = None
    group_id: str | None = None
    order: int | None = None


class PurchaseBase(BaseModel):
    quantity: int


class PurchaseComplete(PurchaseBase):
    user_id: str
    product_variant_id: UUID
    validated: bool
    purchased_on: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseReturn(PurchaseComplete):
    price: int
    product: ProductComplete
    seller: SellerComplete

    model_config = ConfigDict(from_attributes=True)


class PurchaseEdit(BaseModel):
    quantity: int | None = None


class SignatureBase(BaseModel):
    signature_type: DocumentSignatureType
    numeric_signature_id: str | None = None


class SignatureComplete(SignatureBase):
    user_id: str
    document_id: UUID

    model_config = ConfigDict(from_attributes=True)


class PaymentBase(BaseModel):
    total: int
    payment_type: PaymentType


class PaymentComplete(PaymentBase):
    id: UUID
    user_id: str

    model_config = ConfigDict(from_attributes=True)


class Status(BaseCoreData):
    status: PurchasesStatus = PurchasesStatus.pending


class PaymentCart(BaseModel):
    purchase_ids: list[UUID] = []


class PaymentUrl(BaseModel):
    url: str


class NewUserWSMessageModel(WSMessageModel):
    command: Literal["NEW_USER"] = "NEW_USER"
    data: PurchasesUser


class UpdateUserWSMessageModel(WSMessageModel):
    command: Literal["UPDATE_USER"] = "UPDATE_USER"
    data: PurchasesUser


class CustomDataFieldBase(BaseModel):
    name: str


class CustomDataFieldComplete(CustomDataFieldBase):
    id: UUID
    product_id: UUID

    model_config = ConfigDict(from_attributes=True)


class CustomDataBase(BaseModel):
    value: str


class CustomDataComplete(CustomDataBase):
    field_id: UUID
    user_id: UUID
    field: CustomDataFieldComplete

    model_config = ConfigDict(from_attributes=True)


class ResultRequest(BaseModel):
    emails: list[str]
