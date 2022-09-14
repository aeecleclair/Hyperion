"""Models file for amap"""
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.models_core import CoreUser
from app.utils.types.amap_types import AmapSlotType


class Category(Base):
    __tablename__ = "grocery_category"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, index=True, nullable=False, unique=True)


class Product(Base):
    __tablename__ = "grocery_product"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, index=True, nullable=False, unique=True)
    category_id: str = Column(String, nullable=False)
    quantity: int = Column(Integer, nullable=False)
    expiration: date = Column(Date, nullable=False)
    barcode: str = Column(String, index=True, nullable=False, unique=True)
    price: float = Column(Float, nullable=False)


class Checkout(Base):
    __tablename__ = "grocery_checkout"

    id: str = Column(String, primary_key=True, index=True)
    date: datetime = Column(DateTime, nullable=False)
    vendor_id: str = Column(String, nullable=False)
    # TODO: do we keep this?
    buyer_id: str = Column(String, nullable=False)
    total: float = Column(Float, nullable=False)


class CheckoutItem(Base):
    __tablename__ = "grocery_checkout_item"
    product_id: str = Column(String, nullable=False)
    checkout_id: str = Column(String, nullable=False)
