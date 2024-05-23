from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.cdr.types_cdr import (
    AvailableMembership,
    CdrStatus,
    DocumentSignatureType,
    PaymentType,
)
from app.types.core_data import BaseCoreData


class ProductBase(BaseModel):
    name: str
    description: str | None = None
    seller_id: UUID
    available_online: bool
    unique: bool


class ProductComplete(ProductBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class ProductEdit(BaseModel):
    name: str | None = None
    description: str | None = None
    available_online: bool | None = None
    unique: bool | None = None


class SellerBase(BaseModel):
    name: str
    group_id: UUID
    order: int


class SellerComplete(SellerBase):
    id: UUID
    products: list[ProductComplete] = []

    model_config = ConfigDict(from_attributes=True)


class SellerEdit(BaseModel):
    name: str | None = None
    group_id: UUID | None = None
    order: int | None = None


class ProductVariantBase(BaseModel):
    name: str
    description: str | None = None
    price: int
    enabled: bool


class ProductVariantComplete(ProductVariantBase):
    id: UUID
    product_id: UUID

    model_config = ConfigDict(from_attributes=True)


class ProductVariantEdit(BaseModel):
    name: str | None = None
    description: str | None = None
    price: int | None = None
    enabled: bool | None = None


class DocumentBase(BaseModel):
    name: str


class DocumentComplete(DocumentBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class PurchaseBase(BaseModel):
    quantity: int
    paid: bool

    model_config = ConfigDict(from_attributes=True)


class PurchaseComplete(PurchaseBase):
    user_id: UUID
    product_variant_id: UUID

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


class Status(BaseCoreData):
    status: CdrStatus = CdrStatus.pending
