from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.reception.types_reception import (
    AvailableMembership,
    DocumentSignatureType,
    PaymentType,
)


class SellerBase(BaseModel):
    name: str
    group_id: UUID
    order: int


class SellerComplete(SellerBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class SellerEdit(BaseModel):
    name: str | None = None
    group_id: UUID | None = None
    order: int | None = None


class ProductBase(BaseModel):
    name: str
    description: str | None = None
    seller_id: UUID
    public_display: bool


class ProductComplete(SellerBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class ProductEdit(BaseModel):
    name: str | None = None
    description: str | None = None
    public_display: bool | None = None


class ProductVariantBase(BaseModel):
    name: str
    description: str | None = None
    price: int
    enabled: bool
    unique: bool


class ProductVariantComplete(SellerBase):
    id: UUID
    product_id: UUID

    model_config = ConfigDict(from_attributes=True)


class ProductVariantEdit(BaseModel):
    name: str | None = None
    description: str | None = None
    price: int | None = None
    enabled: bool | None = None
    unique: bool | None = None


class DocumentBase(BaseModel):
    name: str


class DocumentComplete(SellerBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class PurchaseBase(BaseModel):
    user_id: UUID
    product_variant_id: UUID
    quantity: int
    paid: bool


class PurchaseComplete(SellerBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class PurchaseEdit(BaseModel):
    quantity: int | None = None


class Signature(BaseModel):
    user_id: UUID
    document_id: UUID
    signature_type: DocumentSignatureType
    numeric_signature_id: str | None = None


class CurriculumBase(BaseModel):
    name: str


class CurriculumComplete(CurriculumBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class PaymentBase(BaseModel):
    user_id: UUID
    total: int
    payment_type: PaymentType


class PaymentComplete(PaymentBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class MembershipBase(BaseModel):
    user_id: UUID
    membership: AvailableMembership
    start_date: date
    end_date: date


class MembershipComplete(MembershipBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class MembershipEdit(BaseModel):
    end_date: date | None = None


class Status(BaseModel):
    editable: bool
