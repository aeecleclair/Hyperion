from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.core.memberships import schemas_memberships
from app.core.users.schemas_users import CoreUserSimple
from app.modules.cdr.types_cdr import (
    CdrStatus,
    DocumentSignatureType,
    PaymentType,
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


class CdrUserPreview(CoreUserSimple):
    curriculum: CurriculumComplete | None = None


class CdrUser(CdrUserPreview):
    promo: int | None = None
    email: str
    birthday: date | None = None
    phone: str | None = None
    floor: FloorsType | None = None

    model_config = ConfigDict(from_attributes=True)


class CdrUserUpdate(BaseModel):
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


class GenerateTicketBase(BaseModel):
    name: str
    max_use: int
    expiration: datetime


class GenerateTicketComplete(GenerateTicketBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class GenerateTicketEdit(BaseModel):
    max_use: int | None = None
    expiration: datetime | None = None


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
    year: int


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


class ProductBase(BaseModel):
    name_fr: str
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    available_online: bool
    needs_validation: bool = True
    related_membership: schemas_memberships.MembershipSimple | None = None
    tickets: list[GenerateTicketBase] = []
    product_constraints: list[UUID]
    document_constraints: list[UUID]
    year: int | None = None


class ProductCompleteNoConstraint(BaseModel):
    name_fr: str
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    available_online: bool
    needs_validation: bool
    id: UUID
    seller_id: UUID
    variants: list[ProductVariantComplete] = []
    related_membership: schemas_memberships.MembershipSimple | None = None
    tickets: list[GenerateTicketComplete]

    model_config = ConfigDict(from_attributes=True)


class ProductComplete(BaseModel):
    name_fr: str
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    available_online: bool
    needs_validation: bool
    id: UUID
    seller_id: UUID
    variants: list[ProductVariantComplete] = []
    related_membership: schemas_memberships.MembershipSimple | None = None
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
    related_membership: schemas_memberships.MembershipSimple | None = None
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
    year: int


class PaymentComplete(PaymentBase):
    id: UUID
    user_id: str

    model_config = ConfigDict(from_attributes=True)


class Status(BaseCoreData):
    status: CdrStatus = CdrStatus.pending


class PaymentUrl(BaseModel):
    url: str


class UserTicket(CoreUserSimple):
    promo: int | None = None
    floor: FloorsType | None = None
    created_on: datetime | None = None


class Ticket(BaseModel):
    id: UUID
    product_variant: ProductVariantComplete
    user: UserTicket
    scan_left: int
    tags: str
    expiration: datetime
    name: str


class TicketScan(BaseModel):
    tag: Annotated[
        str,
        StringConstraints(to_lower=True, strip_whitespace=True, pattern=r"[^,]+"),
    ]


class TicketSecret(BaseModel):
    qr_code_secret: UUID


class NewUserWSMessageModel(WSMessageModel):
    command: Literal["NEW_USER"] = "NEW_USER"
    data: CdrUser


class UpdateUserWSMessageModel(WSMessageModel):
    command: Literal["UPDATE_USER"] = "UPDATE_USER"
    data: CdrUser


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
