"""Schemas file for endpoint /sdec_facturation"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.modules.sdec_facturation.types_sdec_facturation import (
    AssociationStructureType,
    AssociationType,
    IndividualCategoryType,
    ProductCategoryType,
    RoleType,
)


class MemberBase(BaseModel):
    name: str
    mandate: int
    role: RoleType
    visible: bool = True


class MemberComplete(MemberBase):
    id: UUID
    modified_date: date


class MandateComplete(BaseModel):
    year: int
    name: str


class MandateUpdate(BaseModel):
    name: str


class AssociationBase(BaseModel):
    name: str
    type: AssociationType
    structure: AssociationStructureType
    visible: bool = True


class AssociationComplete(AssociationBase):
    id: UUID
    modified_date: date


class ProductBase(BaseModel):
    code: str
    name: str
    category: ProductCategoryType
    for_sale: bool = True


class ProductComplete(ProductBase):
    id: UUID
    creation_date: date


class ProductUpdate(BaseModel):
    name: str | None = None
    category: ProductCategoryType | None = None
    for_sale: bool | None = None


class ProductPriceBase(BaseModel):
    product_id: UUID
    individual_price: float
    association_price: float
    ae_price: float


class ProductPriceComplete(ProductPriceBase):
    id: UUID
    effective_date: date


class ProductPriceUpdate(BaseModel):
    individual_price: float
    association_price: float
    ae_price: float


class ProductAndPriceBase(ProductBase):
    individual_price: float
    association_price: float
    ae_price: float


class ProductAndPriceComplete(ProductAndPriceBase):
    id: UUID
    creation_date: date
    effective_date: date


class OrderBase(BaseModel):
    association_id: UUID
    member_id: UUID
    order: str
    valid: bool = True


class OrderComplete(OrderBase):
    id: UUID
    creation_date: date


class OrderUpdate(BaseModel):
    order: str | None = None


class FactureAssociationBase(BaseModel):
    facture_number: str
    member_id: UUID
    association_id: UUID
    start_date: date
    end_date: date
    price: float
    valid: bool = True
    paid: bool = False
    payment_date: date | None = None


class FactureAssociationComplete(FactureAssociationBase):
    facture_date: date
    id: UUID


class FactureAssociationUpdate(BaseModel):
    paid: bool | None = None


class FactureIndividualBase(BaseModel):
    facture_number: str
    member_id: UUID
    individual_order: str
    individual_category: IndividualCategoryType
    price: float
    firstname: str
    lastname: str
    adresse: str
    postal_code: str
    city: str
    country: str
    valid: bool = True
    paid: bool = False
    payment_date: date | None = None


class FactureIndividualComplete(FactureIndividualBase):
    facture_date: date
    id: UUID


class FactureIndividualUpdate(BaseModel):
    firstname: str | None = None
    lastname: str | None = None
    adresse: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
    paid: bool | None = None
