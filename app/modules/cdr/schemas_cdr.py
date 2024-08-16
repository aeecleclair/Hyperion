from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.schemas_core import CoreUserSimple
from app.modules.cdr.types_cdr import (
    CdrStatus,
    DocumentSignatureType,
    PaymentType,
)
from app.types.core_data import BaseCoreData
from app.types.floors_type import FloorsType
from app.types.membership import AvailableAssociationMembership
from app.types.websocket import WSMessageModel


class NewUserWSMessageModel(WSMessageModel):
    command: Literal["NEW_USER"] = "NEW_USER"
    data: CoreUserSimple


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


class CdrUser(CoreUserSimple):
    curriculum: CurriculumComplete | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductVariantBase(BaseModel):
    name_fr: str
    name_en: str
    description_fr: str | None = None
    description_en: str | None = None
    price: int
    enabled: bool
    unique: bool
    allowed_curriculum: list[UUID]
    related_membership_added_duration: timedelta | None = None


class ProductVariantComplete(BaseModel):
    id: UUID
    product_id: UUID
    name_fr: str
    name_en: str
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
    name_en: str
    description_fr: str | None = None
    description_en: str | None = None
    available_online: bool
    related_membership: AvailableAssociationMembership | None = None
    generate_ticket: bool
    ticket_max_use: int | None = None
    ticket_expiration: datetime | None = None
    product_constraints: list[UUID]
    document_constraints: list[UUID]


class ProductCompleteNoConstraint(BaseModel):
    name_fr: str
    name_en: str
    description_fr: str | None = None
    description_en: str | None = None
    available_online: bool
    id: UUID
    seller_id: UUID
    variants: list[ProductVariantComplete] = []
    related_membership: AvailableAssociationMembership | None = None
    generate_ticket: bool
    ticket_max_use: int | None = None
    ticket_expiration: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductComplete(BaseModel):
    name_fr: str
    name_en: str
    description_fr: str | None = None
    description_en: str | None = None
    available_online: bool
    id: UUID
    seller_id: UUID
    variants: list[ProductVariantComplete] = []
    related_membership: AvailableAssociationMembership | None = None
    generate_ticket: bool
    ticket_max_use: int | None = None
    ticket_expiration: datetime | None = None
    product_constraints: list[ProductCompleteNoConstraint] = []
    document_constraints: list[DocumentComplete] = []

    model_config = ConfigDict(from_attributes=True)


class ProductEdit(BaseModel):
    name_fr: str | None = None
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    description: str | None = None
    available_online: bool | None = None
    related_membership: AvailableAssociationMembership | None = None
    generate_ticket: bool | None = None
    ticket_max_use: int | None = None
    ticket_expiration: datetime | None = None
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
    product: ProductCompleteNoConstraint
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


class MembershipBase(BaseModel):
    membership: AvailableAssociationMembership
    start_date: date
    end_date: date


class MembershipComplete(MembershipBase):
    id: UUID
    user_id: str

    model_config = ConfigDict(from_attributes=True)


class MembershipEdit(BaseModel):
    end_date: date | None = None


class MembershipUserMappingEmail(BaseModel):
    user_email: str
    start_date: date
    end_date: date


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
    scan: int
    tags: str
    expiration: datetime


class TicketScan(BaseModel):
    tag: str


class TicketSecret(BaseModel):
    qr_code_secret: UUID
