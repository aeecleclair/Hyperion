import uuid
from datetime import UTC, datetime

import pytest_asyncio

from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.modules.cdr import models_cdr
from app.modules.cdr.utils_cdr import construct_dataframe_from_users_purchases
from tests.commons import (
    create_api_access_token,
    create_user_with_groups,
)

cdr_admin: models_users.CoreUser
cdr_user1: models_users.CoreUser
cdr_user2: models_users.CoreUser
cdr_user3: models_users.CoreUser

token_admin: str
token_user: str

seller1: models_cdr.Seller
seller2: models_cdr.Seller

product1: models_cdr.CdrProduct
product2: models_cdr.CdrProduct
product3: models_cdr.CdrProduct

product1_variant1: models_cdr.ProductVariant
product1_variant2: models_cdr.ProductVariant
product1_variant3: models_cdr.ProductVariant
product2_variant1: models_cdr.ProductVariant
product3_variant1: models_cdr.ProductVariant

purchase_user1_product1_variant1: models_cdr.Purchase
purchase_user1_product2_variant1: models_cdr.Purchase
purchase_user1_product3_variant1: models_cdr.Purchase
purchase_user2_product1_variant2: models_cdr.Purchase
purchase_user2_product2_variant1: models_cdr.Purchase
purchase_user3_product1_variant3: models_cdr.Purchase
purchase_user3_product3_variant1: models_cdr.Purchase

customdata_field1: models_cdr.CustomDataField
customdata_field2: models_cdr.CustomDataField

customdata_user1: models_cdr.CustomData
customdata_user2: models_cdr.CustomData
customdata_user3: models_cdr.CustomData


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects():
    global cdr_admin
    cdr_admin = await create_user_with_groups(
        [GroupType.admin_cdr],
        email="cdr_admin@etu.ec-lyon.fr",
    )

    global token_admin
    token_admin = create_api_access_token(cdr_admin)

    global cdr_user1
    cdr_user1 = await create_user_with_groups(
        [],
        email="demo@demo.fr",
        name="Demo",
        firstname="Oui",
    )

    global token_user
    token_user = create_api_access_token(cdr_user1)

    global cdr_user2
    cdr_user2 = await create_user_with_groups(
        [],
    )

    global cdr_user3
    cdr_user3 = await create_user_with_groups(
        [],
    )

    global seller1
    seller1 = models_cdr.Seller(
        id=uuid.uuid4(),
        name="BDE",
        group_id=str(GroupType.BDE.value),
        order=1,
    )

    global seller2
    seller2 = models_cdr.Seller(
        id=uuid.uuid4(),
        name="CAA",
        group_id=str(GroupType.CAA.value),
        order=2,
    )

    global product1
    product1 = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=seller1.id,
        name_fr="Produit",
        name_en="Product",
        description_fr="Un Produit",
        description_en="A Product",
        available_online=False,
        needs_validation=True,
    )

    global product2
    product2 = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=seller1.id,
        name_fr="Produit2",
        name_en="Product2",
        description_fr="Un Produit2",
        description_en="A Product2",
        available_online=False,
        needs_validation=True,
    )

    global product3
    product3 = models_cdr.CdrProduct(
        id=uuid.uuid4(),
        seller_id=seller2.id,
        name_fr="Produit3",
        name_en="Product3",
        description_fr="Un Produit3",
        description_en="A Product3",
        available_online=False,
        needs_validation=True,
    )

    global customdata_field1
    customdata_field1 = models_cdr.CustomDataField(
        id=uuid.uuid4(),
        product_id=product1.id,
        name="Champ 1",
    )

    global customdata_field2
    customdata_field2 = models_cdr.CustomDataField(
        id=uuid.uuid4(),
        product_id=product2.id,
        name="Champ 2",
    )

    global product1_variant1
    product1_variant1 = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product1.id,
        name_fr="Variante",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
    )

    global product1_variant2
    product1_variant2 = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product1.id,
        name_fr="Variante2",
        name_en="Variant2",
        price=200,
        unique=False,
        enabled=True,
    )

    global product1_variant3
    product1_variant3 = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product1.id,
        name_fr="Variante3",
        name_en="Variant3",
        price=300,
        unique=False,
        enabled=True,
    )

    global product2_variant1
    product2_variant1 = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product2.id,
        name_fr="Variante",
        name_en="Variant",
        price=100,
        unique=True,
        enabled=True,
    )

    global product3_variant1
    product3_variant1 = models_cdr.ProductVariant(
        id=uuid.uuid4(),
        product_id=product3.id,
        name_fr="Variante",
        name_en="Variant",
        price=100,
        unique=False,
        enabled=True,
    )

    global purchase_user1_product1_variant1
    purchase_user1_product1_variant1 = models_cdr.Purchase(
        user_id=cdr_user1.id,
        product_variant_id=product1_variant1.id,
        quantity=10,
        validated=True,
        purchased_on=datetime.now(UTC),
    )

    global purchase_user1_product2_variant1
    purchase_user1_product2_variant1 = models_cdr.Purchase(
        user_id=cdr_user1.id,
        product_variant_id=product2_variant1.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )

    global purchase_user1_product3_variant1
    purchase_user1_product3_variant1 = models_cdr.Purchase(
        user_id=cdr_user1.id,
        product_variant_id=product3_variant1.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )

    global purchase_user2_product1_variant2
    purchase_user2_product1_variant2 = models_cdr.Purchase(
        user_id=cdr_user2.id,
        product_variant_id=product1_variant2.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )

    global purchase_user2_product2_variant1
    purchase_user2_product2_variant1 = models_cdr.Purchase(
        user_id=cdr_user2.id,
        product_variant_id=product2_variant1.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )

    global purchase_user3_product1_variant3
    purchase_user3_product1_variant3 = models_cdr.Purchase(
        user_id=cdr_user3.id,
        product_variant_id=product1_variant3.id,
        quantity=50,
        validated=True,
        purchased_on=datetime.now(UTC),
    )

    global purchase_user3_product3_variant1
    purchase_user3_product3_variant1 = models_cdr.Purchase(
        user_id=cdr_user3.id,
        product_variant_id=product3_variant1.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )

    global customdata_user1
    customdata_user1 = models_cdr.CustomData(
        user_id=cdr_user1.id,
        field_id=customdata_field1.id,
        value="Value 1",
    )

    global customdata_user2
    customdata_user2 = models_cdr.CustomData(
        user_id=cdr_user2.id,
        field_id=customdata_field1.id,
        value="Value 2",
    )

    global customdata_user3
    customdata_user3 = models_cdr.CustomData(
        user_id=cdr_user3.id,
        field_id=customdata_field1.id,
        value="Value 3",
    )


def test_construct_dataframe_from_users_purchases():
    users_purchases = {
        cdr_user1.id: [
            purchase_user1_product1_variant1,
            purchase_user1_product2_variant1,
        ],
        cdr_user2.id: [
            purchase_user2_product1_variant2,
            purchase_user2_product2_variant1,
        ],
        cdr_user3.id: [
            purchase_user3_product1_variant3,
        ],
    }
    users = [cdr_user1, cdr_user2, cdr_user3]
    products = [product1, product2]
    product_variants = [
        product1_variant1,
        product1_variant2,
        product1_variant3,
        product2_variant1,
    ]
    customdata_fields = {
        product1.id: [customdata_field1],
        product2.id: [customdata_field2],
    }
    users_answers = {
        cdr_user1.id: [customdata_user1],
        cdr_user2.id: [customdata_user2],
        cdr_user3.id: [customdata_user3],
    }

    df = construct_dataframe_from_users_purchases(
        users=users,
        products=products,
        variants=product_variants,
        users_purchases=users_purchases,
        data_fields=customdata_fields,
        users_answers=users_answers,
    )
    assert df.shape == (4, 12)
    assert df.columns.tolist() == [
        "Nom",
        "Prénom",
        "Surnom",
        "Email",
        f"1. {product1.name_fr} : {product1_variant1.name_fr}",
        f"2. {product1.name_fr} : {product1_variant2.name_fr}",
        f"3. {product1.name_fr} : {product1_variant3.name_fr}",
        f"4. {product1.name_fr} : {customdata_field1.name}",
        f"5. {product2.name_fr} : {product2_variant1.name_fr}",
        f"6. {product2.name_fr} : {customdata_field2.name}",
        "Panier payé",
        "Commentaire",
    ]
    for user_id in [user.id for user in users]:
        assert user_id in df.index
    assert list(df.loc[cdr_user1.id]) == [
        cdr_user1.name,
        cdr_user1.firstname,
        "",
        cdr_user1.email,
        10,
        "",
        "",
        "Value 1",
        1,
        "",
        False,
        "Manquant : \n-Produit2 : Variante",
    ]
    assert list(df.loc[cdr_user2.id]) == [
        cdr_user2.name,
        cdr_user2.firstname,
        "",
        cdr_user2.email,
        "",
        1,
        "",
        "Value 2",
        1,
        "",
        False,
        "Manquant : \n-Produit : Variante2\n-Produit2 : Variante",
    ]
    assert list(df.loc[cdr_user3.id]) == [
        cdr_user3.name,
        cdr_user3.firstname,
        "",
        cdr_user3.email,
        "",
        "",
        50,
        "Value 3",
        "",
        "",
        True,
        "",
    ]
