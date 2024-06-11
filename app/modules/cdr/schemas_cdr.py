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


class ProductVariantBase(BaseModel):
    name_fr: str
    name_en: str
    description_fr: str | None = None
    description_en: str | None = None
    price: int
    enabled: bool
    unique: bool


class ProductVariantComplete(ProductVariantBase):
    id: UUID
    product_id: UUID
    allowed_curriculum: list[CurriculumComplete] = []

    model_config = ConfigDict(from_attributes=True)


class ProductVariantEdit(BaseModel):
    name_fr: str | None = None
    name_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    price: int | None = None
    enabled: bool | None = None
    unique: bool | None = None


class ProductBase(BaseModel):
    name_fr: str
    name_en: str
    description_fr: str | None = None
    description_en: str | None = None
    available_online: bool


class ProductCompleteNoConstraint(ProductBase):
    id: UUID
    seller_id: UUID
    variants: list[ProductVariantComplete] = []
    related_membership: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductComplete(ProductBase):
    id: UUID
    seller_id: UUID
    variants: list[ProductVariantComplete] = []
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
    related_membership: str | None = None


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
    membership: AvailableMembership
    start_date: date
    end_date: date


class MembershipComplete(MembershipBase):
    id: UUID
    user_id: str

    model_config = ConfigDict(from_attributes=True)


class MembershipEdit(BaseModel):
    end_date: date | None = None


class Status(BaseCoreData):
    status: CdrStatus = CdrStatus.pending
