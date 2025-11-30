"""Schemas file for endpoint /amap"""

from collections.abc import Sequence
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.users.schemas_users import CoreUserSimple
from app.modules.amap.types_amap import AmapSlotType, DeliveryStatusType


class Rights(BaseModel):
    view: bool
    manage: bool
    amap_id: str
    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    """Base schema for AMAP products"""

    name: str
    price: int


class ProductSimple(ProductBase):
    category: str


class ProductEdit(BaseModel):
    category: str | None = None
    name: str | None = None
    price: int | None = None


class ProductComplete(ProductSimple):
    id: str
    model_config = ConfigDict(from_attributes=True)


class ProductQuantity(BaseModel):
    quantity: int
    product: ProductComplete
    model_config = ConfigDict(from_attributes=True)


class DeliveryBase(BaseModel):
    """Base schema for AMAP deliveries"""

    name: str
    delivery_date: date
    products_ids: list[str] = []


class DeliveryComplete(DeliveryBase):
    id: str
    status: DeliveryStatusType
    model_config = ConfigDict(from_attributes=True)


class DeliveryUpdate(BaseModel):
    name: str | None = None
    delivery_date: date | None = None


class DeliveryProductsUpdate(BaseModel):
    products_ids: list[str]


class OrderBase(BaseModel):
    user_id: str
    delivery_id: str
    products_ids: list[str]
    collection_slot: AmapSlotType
    products_quantity: list[int]


class OrderComplete(OrderBase):
    order_id: str
    amount: int
    ordering_date: datetime
    model_config = ConfigDict(from_attributes=True)


class OrderReturn(BaseModel):
    user: CoreUserSimple
    delivery_id: str
    delivery_name: str
    productsdetail: Sequence[ProductQuantity]
    collection_slot: AmapSlotType
    order_id: str
    amount: int
    ordering_date: datetime
    delivery_date: date
    model_config = ConfigDict(from_attributes=True)


class OrderEdit(BaseModel):
    products_ids: list[str] | None = None
    collection_slot: AmapSlotType | None = None
    products_quantity: list[int] | None = None
    model_config = ConfigDict(from_attributes=True)


class DeliveryReturn(BaseModel):
    name: str
    delivery_date: date
    products: list[ProductComplete] = []
    id: str
    status: DeliveryStatusType
    model_config = ConfigDict(from_attributes=True)


class AddProductDelivery(BaseModel):
    product_id: str
    delivery_id: str


class CashBase(BaseModel):
    balance: int
    user_id: str
    model_config = ConfigDict(from_attributes=True)


class CashComplete(CashBase):
    user: CoreUserSimple


class CashEdit(BaseModel):
    balance: int


class Information(BaseModel):
    manager: str
    link: str
    description: str
    model_config = ConfigDict(from_attributes=True)


class InformationEdit(BaseModel):
    manager: str | None = None
    link: str | None = None
    description: str | None = None
