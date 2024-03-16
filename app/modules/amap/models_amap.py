"""Models file for amap"""

from datetime import date, datetime

from sqlalchemy import Date, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models_core import CoreUser
from app.database import Base
from app.modules.amap.types_amap import AmapSlotType, DeliveryStatusType
from app.utils.types.datetime import TZDateTime


class AmapOrderContent(Base):
    __tablename__ = "amap_order_content"
    product_id: Mapped[str] = mapped_column(
        ForeignKey("amap_product.id"),
        primary_key=True,
    )
    order_id: Mapped[str] = mapped_column(
        ForeignKey("amap_order.order_id"),
        primary_key=True,
    )
    quantity: Mapped[int] = mapped_column(Integer)
    product: Mapped["Product"] = relationship("Product")


class AmapDeliveryContent(Base):
    __tablename__ = "amap_delivery_content"
    product_id: Mapped[str] = mapped_column(
        ForeignKey("amap_product.id"),
        primary_key=True,
    )
    delivery_id: Mapped[str] = mapped_column(
        ForeignKey("amap_delivery.id"),
        primary_key=True,
    )


class Product(Base):
    __tablename__ = "amap_product"

    id: Mapped[Mapped[str]] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[Mapped[str]] = mapped_column(
        String,
        index=True,
        nullable=False,
        unique=True,
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String, index=True, nullable=False)


class Delivery(Base):
    __tablename__ = "amap_delivery"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    delivery_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        unique=False,
        index=True,
    )
    products: Mapped[list[Product]] = relationship(
        "Product",
        secondary="amap_delivery_content",
    )
    orders: Mapped[list["Order"]] = relationship("Order")
    status: Mapped[DeliveryStatusType] = mapped_column(String, nullable=False)


class Order(Base):
    __tablename__ = "amap_order"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("core_user.id"),
        nullable=False,
    )
    user: Mapped[CoreUser] = relationship(
        "CoreUser",
    )
    delivery_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("amap_delivery.id"),
        index=True,
        nullable=False,
    )
    order_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    products: Mapped[list[Product]] = relationship(
        "Product",
        secondary="amap_order_content",
        viewonly=True,
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    collection_slot: Mapped[AmapSlotType] = mapped_column(
        Enum(AmapSlotType),
        nullable=False,
    )
    ordering_date: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)


class Cash(Base):
    __tablename__ = "amap_cash"

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    user: Mapped[CoreUser] = relationship("CoreUser")
    balance: Mapped[float] = mapped_column(Float, nullable=False)


class AmapInformation(Base):
    __tablename__ = "amap_information"

    # unique_id should always be `information`
    unique_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    manager: Mapped[str] = mapped_column(String, nullable=False)
    link: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
