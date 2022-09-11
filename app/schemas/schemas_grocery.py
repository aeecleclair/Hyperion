from datetime import date, datetime

from pydantic import BaseModel


class ProductBase(BaseModel):
    name: str
    category_id: str
    quantity: str
    expiration: date
    barcode: str
    price: int

    class Config:
        orm_mode = True


class Product(ProductBase):
    id: str


class ProductUpdate(BaseModel):
    name: str | None = None
    category_id: str | None = None
    quantity: str | None = None
    expiration: date | None = None
    barcode: str | None = None
    price: int | None = None


class CategoryBase(BaseModel):
    name: str

    class Config:
        orm_mode = True


class Category(CategoryBase):
    id: str


class CategoryUpdate(BaseModel):
    name: str | None = None


class Checkout(BaseModel):
    id: str
    datetime: datetime
    vendor_id: str
    # TODO: do we keep this?
    buyer_id: str
    total: int


class CheckoutItem(BaseModel):
    product_id: str
    checkout_id: str
