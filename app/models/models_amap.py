"""model file for amap"""
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, String, Table
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.models_core import CoreUser
from app.utils.types.groups_type import AmapSlotType


class AmapOrderContent(Base):
    __tablename__ = "amap_order_content"
    product_id: str = Column(ForeignKey("amap_product.id"), primary_key=True)
    order_id: str = Column(ForeignKey("amap_order.orderId"), primary_key=True)


class AmapDeliveryContent(Base):
    __tablename__ = "amap_delivery_content"
    product_id: str = Column(ForeignKey("amap_product.id"), primary_key=True)
    delivery_id: str = Column(
        ForeignKey("amap_delivery.deliveryDate"), primary_key=True
    )


class Product(Base):
    __tablename__ = "amap_product"

    id: str = Column(String, primary_key=True, index=True)
    name: str = Column(String, index=True, nullable=False, unique=True)
    price: float = Column(Float, nullable=False)
    category: str = Column(String, index=True, nullable=False)


class Order(Base):
    __tablename__ = "amap_order"

    userId: str = Column(String, ForeignKey("core_user.id"))
    user: CoreUser = relationship(
        "CoreUser",
    )
    deliveryId: str = Column(String, index=True, nullable=True)
    orderId: str = Column(String, primary_key=True, index=True)
    products: list["Product"] = relationship(
        "Product",
        secondary="amap_order_content",
    )
    amount: float = Column(Float, nullable=False)
    collectionSlot: AmapSlotType = Column(Enum(AmapSlotType), nullable=False)
    orderingDate: datetime = Column(DateTime, nullable=False)
    deliveryDate: date = Column(Date, nullable=False)


class Delivery(Base):
    __tablename__ = "amap_delivery"

    deliveryDate: datetime = Column(Date, primary_key=True)
    products: list["Product"] = relationship(
        "Product",
        secondary="amap_delivery_content",
    )


class Cash(Base):
    __tablename__ = "amap_cash"

    userId: str = Column(String, ForeignKey("core_user.id"), primary_key=True)
    user: CoreUser = relationship(
        "CoreUser",
    )
    balance: float = Column(Float, nullable=False)
