"""Schemas file for endpoint /sdec-facturation"""

import uuid
from datetime import date

from pydantic import BaseModel

from app.modules.sdec_facturation.types_sdec_facturation import (
    AssociationStructureType,
    AssociationType,
    IndividualCategoryType,
    RoleType,
)


class MemberBase(BaseModel):
    name: str
    mandate: int
    role: RoleType
    visible: bool = True


class MemberComplete(MemberBase):
    id: uuid.UUID
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
    id: uuid.UUID
    modified_date: date


class ProductBase(BaseModel):
    code: str
    name: str
    individual_price: float
    association_price: float
    ae_price: float
    category: str
    for_sale: bool = True


class ProductComplete(ProductBase):
    id: uuid.UUID
    creation_date: date


class ProductMinorUpdate(BaseModel):
    name: str | None = None
    category: str | None = None


class ProductUpdate(BaseModel):
    individual_price: float
    association_price: float
    ae_price: float


class OrderBase(BaseModel):
    association_id: uuid.UUID
    member_id: uuid.UUID
    order: str
    valid: bool = True


class OrderComplete(OrderBase):
    id: uuid.UUID
    creation_date: date


class OrderUpdate(BaseModel):
    valid: bool
    order: str


class FactureAssociationBase(BaseModel):
    facture_number: str
    member_id: uuid.UUID
    association_id: uuid.UUID
    association_order: list[int]
    price: float
    valid: bool
    paid: bool
    payment_date: date | None = None


class FactureAssociationComplete(FactureAssociationBase):
    facture_date: date
    id: uuid.UUID


class FactureUpdate(BaseModel):
    valid: bool | None = None
    paid: bool | None = None
    payment_date: date | None = None


class FactureIndividualBase(BaseModel):
    facture_number: str
    member_id: uuid.UUID
    individual_order: str
    individual_category: IndividualCategoryType
    price: float
    firstname: str
    lastname: str
    adresse: str
    postal_code: str
    city: str
    country: str
    valid: bool
    paid: bool
    payment_date: date | None = None


class FactureIndividualComplete(FactureIndividualBase):
    facture_date: date
    id: uuid.UUID
