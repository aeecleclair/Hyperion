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


class AmapOrderContent(Base):
    __tablename__ = "amap_order_content"
    product_id: str = Column(ForeignKey("amap_product.id"), primary_key=True)
    order_id: str = Column(ForeignKey("amap_order.order_id"), primary_key=True)
    quantity: int = Column(Integer)


class AmapDeliveryContent(Base):
    __tablename__ = "amap_delivery_content"
    product_id: str = Column(ForeignKey("amap_product.id"), primary_key=True)
    delivery_id: str = Column(ForeignKey("amap_delivery.id"), primary_key=True)


class Product(Base):
    __tablename__ = "amap_product"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, index=True, nullable=False, unique=True)
    price: float = Column(Float, nullable=False)
    category: str = Column(String, index=True, nullable=False)


class Delivery(Base):
    __tablename__ = "amap_delivery"

    id: str = Column(String, primary_key=True, index=True)
    delivery_date: date = Column(Date, nullable=False, unique=True, index=True)
    products: list[Product] = relationship(
        "Product",
        secondary="amap_delivery_content",
    )
    orders: list["Order"] = relationship("Order", back_populates="delivery")
    locked: bool = Column(Boolean, nullable=False)


class Order(Base):
    __tablename__ = "amap_order"

    user_id: str = Column(String, ForeignKey("core_user.id"), primary_key=True)
    user: CoreUser = relationship(
        "CoreUser",
    )
    delivery_id: str = Column(
        String, ForeignKey("amap_delivery.id"), index=True, nullable=True
    )
    delivery: Delivery = relationship("Delivery", back_populates="orders")
    order_id: str = Column(String, primary_key=True, index=True)
    products: list[Product] = relationship(
        "Product",
        secondary="amap_order_content",
    )
    amount: float = Column(Float, nullable=False)
    collection_slot: AmapSlotType = Column(Enum(AmapSlotType), nullable=False)
    ordering_date: datetime = Column(DateTime, nullable=False)
    delivery_date: date = Column(Date, nullable=False)


class Cash(Base):
    __tablename__ = "amap_cash"

    user_id: str = Column(String, ForeignKey("core_user.id"), primary_key=True)
    user: CoreUser = relationship("CoreUser")
    balance: float = Column(Float, nullable=False)
