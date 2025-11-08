"""Models file for SDeC facturation website"""

from datetime import date
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.sdec_facturation.types_sdec_facturation import (
    AssociationStructureType,
    AssociationType,
    IndividualCategoryType,
    RoleType,
)
from app.types.sqlalchemy import Base, PrimaryKey


class Member(Base):
    __tablename__ = "sdec_facturation_member"
    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(index=True)
    mandate: Mapped[int] = mapped_column(ForeignKey("sdec_facturation_mandate.year"))
    role: Mapped[RoleType]
    modified_date: Mapped[date]
    visible: Mapped[bool] = mapped_column(default=True)


class Mandate(Base):
    __tablename__ = "sdec_facturation_mandate"
    year: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(index=True)


class Association(Base):
    __tablename__ = "sdec_facturation_association"
    id: Mapped[PrimaryKey]
    name: Mapped[str] = mapped_column(index=True)
    type: Mapped[AssociationType]
    structure: Mapped[AssociationStructureType]
    modified_date: Mapped[date]
    visible: Mapped[bool] = mapped_column(default=True)


class Product(Base):
    __tablename__ = "sdec_facturation_product"
    id: Mapped[PrimaryKey]
    code: Mapped[str]
    name: Mapped[str]
    individual_price: Mapped[float]
    association_price: Mapped[float]
    ae_price: Mapped[float]
    category: Mapped[str]
    creation_date: Mapped[date]
    for_sale: Mapped[bool] = mapped_column(default=True)


class Order(Base):
    __tablename__ = "sdec_facturation_order"
    id: Mapped[PrimaryKey]
    association_id: Mapped[UUID] = mapped_column(
        ForeignKey("sdec_facturation_association.id"),
    )
    member_id: Mapped[UUID] = mapped_column(ForeignKey("sdec_facturation_member.id"))
    order: Mapped[str]
    creation_date: Mapped[date]
    valid: Mapped[bool] = mapped_column(default=True)


class FactureAssociation(Base):
    __tablename__ = "sdec_facturation_facture_association"
    id: Mapped[PrimaryKey]
    facture_number: Mapped[str] = mapped_column(unique=True)
    member_id: Mapped[UUID] = mapped_column(ForeignKey("sdec_facturation_member.id"))
    association_id: Mapped[UUID] = mapped_column(
        ForeignKey("sdec_facturation_association.id"),
    )
    association_order: Mapped[str]
    price: Mapped[float]
    facture_date: Mapped[date]
    valid: Mapped[bool]
    paid: Mapped[bool]
    payment_date: Mapped[date | None] = mapped_column(default=None)


class FactureIndividual(Base):
    __tablename__ = "sdec_facturation_facture_individual"
    id: Mapped[PrimaryKey]
    facture_number: Mapped[str] = mapped_column(unique=True)
    member_id: Mapped[UUID] = mapped_column(ForeignKey("sdec_facturation_member.id"))
    individual_order: Mapped[str]
    individual_category: Mapped[IndividualCategoryType]
    price: Mapped[float]
    facture_date: Mapped[date]
    firstname: Mapped[str]
    lastname: Mapped[str]
    adresse: Mapped[str]
    postal_code: Mapped[str]
    city: Mapped[str]
    country: Mapped[str]
    valid: Mapped[bool]
    paid: Mapped[bool]
    payment_date: Mapped[date | None] = mapped_column(default=None)
