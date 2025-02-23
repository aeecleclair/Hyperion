"""Models file for amap"""

from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.users.models_users import CoreUser
from app.modules.amap.types_amap import AmapSlotType, DeliveryStatusType
from app.types.sqlalchemy import Base


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
    quantity: Mapped[int]
    product: Mapped["Product"] = relationship("Product", init=False)


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

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        index=True,
        unique=True,
    )
    price: Mapped[float]
    category: Mapped[str] = mapped_column(index=True)


class Delivery(Base):
    __tablename__ = "amap_delivery"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)
    delivery_date: Mapped[date] = mapped_column(
        unique=False,
        index=True,
    )
    status: Mapped[DeliveryStatusType] = mapped_column(String)
    orders: Mapped[list["Order"]] = relationship("Order", init=False)
    products: Mapped[list[Product]] = relationship(
        "Product",
        secondary="amap_delivery_content",
        default_factory=list,
    )


class Order(Base):
    __tablename__ = "amap_order"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
    )
    delivery_id: Mapped[str] = mapped_column(
        ForeignKey("amap_delivery.id"),
        index=True,
    )
    order_id: Mapped[str] = mapped_column(primary_key=True, index=True)
    amount: Mapped[float]
    collection_slot: Mapped[AmapSlotType]
    ordering_date: Mapped[datetime]
    delivery_date: Mapped[date]
    user: Mapped[CoreUser] = relationship(
        "CoreUser",
        init=False,
    )
    products: Mapped[list[Product]] = relationship(
        "Product",
        secondary="amap_order_content",
        viewonly=True,
        default_factory=list,
    )


class Cash(Base):
    __tablename__ = "amap_cash"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"),
        primary_key=True,
    )
    balance: Mapped[float]
    user: Mapped[CoreUser] = relationship("CoreUser", init=False)


class AmapInformation(Base):
    __tablename__ = "amap_information"

    # unique_id should always be `information`
    unique_id: Mapped[str] = mapped_column(primary_key=True, index=True)
    manager: Mapped[str]
    link: Mapped[str]
    description: Mapped[str]
