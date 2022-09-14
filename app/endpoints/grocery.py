"""File defining the API itself, using fastAPI and schemas, and calling the cruds functions"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_grocery, cruds_groups
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.models import models_grocery
from app.schemas import schemas_core, schemas_grocery
from app.utils.types import standard_responses
from app.utils.types.groups_type import AccountType, GroupType
from app.utils.types.tags import Tags

router = APIRouter()


# TODO
# Admin and and all users should be able to access products and catégories
# Do we need to remove price and codebar for users?


@router.get(
    "/grocery/products/",
    response_model=list[schemas_grocery.Product],
    status_code=200,
    tags=[Tags.grocery],
)
async def get_products(
    db: AsyncSession = Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user_a_member_of(GroupType.grocery)),
):
    """
    Get all the products in the database.

    **This endpoint is only usable by members of Grocery group**
    """
    return await cruds_grocery.get_products(db=db)


@router.post(
    "/grocery/products/",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.grocery],
)
async def create_products(
    product: schemas_grocery.ProductBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user_a_member_of(GroupType.grocery)),
):
    """
    Create a new product.

    **This endpoint is only usable by members of Grocery group**
    """
    # We need to make sure the category exists
    category = await cruds_grocery.get_category_by_id(
        category_id=product.category_id, db=db
    )
    if category is None:
        raise HTTPException(status_code=400, detail="Category not found")

    db_product = models_grocery.Product(
        id=str(uuid.uuid4()),
        **product.dict(),
    )

    try:
        await cruds_grocery.create_product(product=db_product, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    return standard_responses.Result(success=True)


@router.patch(
    "/grocery/products/{product_id}",
    status_code=204,
    tags=[Tags.grocery],
)
async def update_current_user(
    product_id: str,
    product_update: schemas_grocery.ProductUpdate,
    db: AsyncSession = Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user_a_member_of(GroupType.grocery)),
):
    """
    Update a product.

    **This endpoint is only usable by members of Grocery group**
    """

    # If the category is modified, we need to make sure it exists
    if product_update.category_id is not None:
        category = await cruds_grocery.get_category_by_id(
            category_id=product_update.category_id, db=db
        )
        if category is None:
            raise HTTPException(status_code=400, detail="Category not found")

    await cruds_grocery.update_product(
        product_id=product_id,
        product_update=product_update,
        db=db,
    )


@router.delete(
    "/grocery/products/{product_id}",
    status_code=204,
    tags=[Tags.grocery],
)
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user_a_member_of(GroupType.grocery)),
):
    """
    Delete a product. This may make a product unavailable in orders.

    **This endpoint is only usable by members of Grocery group**
    """

    # TODO: what happens if a product is deleted while it is in an order?
    await cruds_grocery.delete_product(product_id=product_id, db=db)


@router.get(
    "/grocery/categories/",
    response_model=list[schemas_grocery.Product],
    status_code=200,
    tags=[Tags.grocery],
)
async def get_categories(
    db: AsyncSession = Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user_a_member_of(GroupType.grocery)),
):
    """
    Get all the categories in the database.

    **This endpoint is only usable by members of Grocery group**
    """
    return await cruds_grocery.get_products(db=db)


@router.post(
    "/grocery/categories/",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.grocery],
)
async def create_category(
    category: schemas_grocery.CategoryBase,
    db: AsyncSession = Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user_a_member_of(GroupType.grocery)),
):
    """
    Create a new category.

    **This endpoint is only usable by members of Grocery group**
    """

    db_category = models_grocery.Category(
        id=str(uuid.uuid4()),
        **category.dict(),
    )

    try:
        await cruds_grocery.create_category(category=db_category, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    return standard_responses.Result(success=True)


@router.patch(
    "/grocery/categories/{category_id}",
    status_code=204,
    tags=[Tags.grocery],
)
async def update_category(
    category_id: str,
    category_update: schemas_grocery.CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user_a_member_of(GroupType.grocery)),
):
    """
    Update a category.

    **This endpoint is only usable by members of Grocery group**
    """

    await cruds_grocery.update_category(
        category_id=category_id,
        category_update=category_update,
        db=db,
    )


@router.delete(
    "/grocery/categories/{category_id}",
    status_code=204,
    tags=[Tags.grocery],
)
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    user: schemas_core.CoreUser = Depends(is_user_a_member_of(GroupType.grocery)),
):
    """
    Delete a category. This may make a category unavailable in products.

    **This endpoint is only usable by members of Grocery group**
    """

    # TODO: what happens if a category is deleted while it is in a product?
    await cruds_grocery.delete_category(category_id=category_id, db=db)
