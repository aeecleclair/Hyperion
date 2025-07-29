from datetime import UTC, datetime
from uuid import uuid4

import pytest_asyncio

from app.core.groups.groups_type import GroupType
from app.core.payment import models_payment
from app.core.schools import models_schools
from app.core.schools.schools_type import SchoolType
from app.core.users import models_users
from app.modules.sport_competition import models_sport_competition
from app.modules.sport_competition.types_sport_competition import (
    ProductPublicType,
    ProductSchoolType,
    SportCategory,
)
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

school_from_lyon: models_schools.CoreSchool
school_others: models_schools.CoreSchool

active_edition: models_sport_competition.CompetitionEdition
old_edition: models_sport_competition.CompetitionEdition

admin_user: models_users.CoreUser
user_from_lyon: models_users.CoreUser
user_others: models_users.CoreUser
user_cameraman: models_users.CoreUser
user_pompom: models_users.CoreUser
user_fanfare: models_users.CoreUser
user_volunteer: models_users.CoreUser
user_multiple: models_users.CoreUser
admin_token: str
user_from_lyon_token: str
user_others_token: str
user_cameraman_token: str
user_pompom_token: str
user_fanfare_token: str
user_volunteer_token: str
user_multiple_token: str

competition_user_admin: models_sport_competition.CompetitionUser
competition_user_from_lyon: models_sport_competition.CompetitionUser
competition_user_others: models_sport_competition.CompetitionUser
competition_user_cameraman: models_sport_competition.CompetitionUser
competition_user_pompom: models_sport_competition.CompetitionUser
competition_user_fanfare: models_sport_competition.CompetitionUser
competition_user_volunteer: models_sport_competition.CompetitionUser
competition_user_multiple: models_sport_competition.CompetitionUser

ecl_extension: models_sport_competition.SchoolExtension
school_from_lyon_extension: models_sport_competition.SchoolExtension
school_others_extension: models_sport_competition.SchoolExtension

product1: models_sport_competition.CompetitionProduct
product2: models_sport_competition.CompetitionProduct
product_old_edition: models_sport_competition.CompetitionProduct

variant_for_athlete: models_sport_competition.CompetitionProductVariant
variant_for_cameraman: models_sport_competition.CompetitionProductVariant
variant_for_pompom: models_sport_competition.CompetitionProductVariant
variant_for_fanfare: models_sport_competition.CompetitionProductVariant
variant_for_volunteer: models_sport_competition.CompetitionProductVariant
variant_for_centrale: models_sport_competition.CompetitionProductVariant
variant_for_from_lyon: models_sport_competition.CompetitionProductVariant
variant_for_others: models_sport_competition.CompetitionProductVariant
variant_unique: models_sport_competition.CompetitionProductVariant
variant_disabled: models_sport_competition.CompetitionProductVariant
variant_old_edition: models_sport_competition.CompetitionProductVariant

purchase: models_sport_competition.CompetitionPurchase
payment: models_sport_competition.CompetitionPayment
checkout: models_sport_competition.CompetitionCheckout


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup():
    global school_from_lyon, school_others

    school_from_lyon = models_schools.CoreSchool(
        id=uuid4(),
        name="Lycée de Lyon",
        email_regex=".*@lyon.fr",
    )
    school_others = models_schools.CoreSchool(
        id=uuid4(),
        name="Lycée des Autres",
        email_regex=".*@autres.fr",
    )
    await add_object_to_db(school_from_lyon)
    await add_object_to_db(school_others)

    global active_edition, old_edition

    old_edition = models_sport_competition.CompetitionEdition(
        id=uuid4(),
        name="Edition 2023",
        year=2023,
        start_date=datetime(2023, 1, 1, tzinfo=UTC),
        end_date=datetime(2023, 12, 31, tzinfo=UTC),
        active=False,
        inscription_enabled=False,
    )
    await add_object_to_db(old_edition)
    active_edition = models_sport_competition.CompetitionEdition(
        id=uuid4(),
        name="Edition 2024",
        year=2024,
        start_date=datetime(2024, 1, 1, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, tzinfo=UTC),
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(active_edition)

    global \
        admin_user, \
        user_from_lyon, \
        user_others, \
        user_cameraman, \
        user_pompom, \
        user_fanfare, \
        user_volunteer, \
        user_multiple
    admin_user = await create_user_with_groups(
        [GroupType.competition_admin],
        email="Admin User",
    )
    user_from_lyon = await create_user_with_groups(
        [],
        email="From Lyon User",
        school_id=school_from_lyon.id,
    )
    user_others = await create_user_with_groups(
        [],
        email="Others User",
        school_id=school_others.id,
    )
    user_cameraman = await create_user_with_groups(
        [],
        email="Cameraman User",
    )
    user_pompom = await create_user_with_groups(
        [],
        email="Pompom User",
    )
    user_fanfare = await create_user_with_groups(
        [],
        email="Fanfare User",
    )
    user_volunteer = await create_user_with_groups(
        [],
        email="Volunteer User",
    )
    user_multiple = await create_user_with_groups(
        [],
        email="Multiple Roles User",
    )

    global \
        admin_token, \
        user_from_lyon_token, \
        user_others_token, \
        user_cameraman_token, \
        user_pompom_token, \
        user_fanfare_token, \
        user_volunteer_token, \
        user_multiple_token

    admin_token = create_api_access_token(admin_user)
    user_from_lyon_token = create_api_access_token(user_from_lyon)
    user_others_token = create_api_access_token(user_others)
    user_cameraman_token = create_api_access_token(user_cameraman)
    user_pompom_token = create_api_access_token(user_pompom)
    user_fanfare_token = create_api_access_token(user_fanfare)
    user_volunteer_token = create_api_access_token(user_volunteer)
    user_multiple_token = create_api_access_token(user_multiple)

    global \
        competition_user_admin, \
        competition_user_from_lyon, \
        competition_user_others, \
        competition_user_cameraman, \
        competition_user_pompom, \
        competition_user_fanfare, \
        competition_user_volunteer, \
        competition_user_multiple

    competition_user_admin = models_sport_competition.CompetitionUser(
        user_id=admin_user.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_admin)
    competition_user_from_lyon = models_sport_competition.CompetitionUser(
        user_id=user_from_lyon.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_from_lyon)
    competition_user_others = models_sport_competition.CompetitionUser(
        user_id=user_others.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_others)
    competition_user_cameraman = models_sport_competition.CompetitionUser(
        user_id=user_cameraman.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_cameraman=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_cameraman)
    competition_user_pompom = models_sport_competition.CompetitionUser(
        user_id=user_pompom.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_pompom=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_pompom)
    competition_user_fanfare = models_sport_competition.CompetitionUser(
        user_id=user_fanfare.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_fanfare=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_fanfare)
    competition_user_volunteer = models_sport_competition.CompetitionUser(
        user_id=user_volunteer.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_volunteer=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_volunteer)
    competition_user_multiple = models_sport_competition.CompetitionUser(
        user_id=user_multiple.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        is_cameraman=True,
        is_volunteer=True,
        validated=False,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_multiple)
    global ecl_extension, school_from_lyon_extension, school_others_extension
    ecl_extension = models_sport_competition.SchoolExtension(
        school_id=SchoolType.centrale_lyon.value,
        from_lyon=True,
        active=True,
        inscription_enabled=True,
        ffsu_id=None,
    )
    await add_object_to_db(ecl_extension)
    school_from_lyon_extension = models_sport_competition.SchoolExtension(
        school_id=school_from_lyon.id,
        from_lyon=True,
        active=True,
        inscription_enabled=True,
        ffsu_id=None,
    )
    await add_object_to_db(school_from_lyon_extension)
    school_others_extension = models_sport_competition.SchoolExtension(
        school_id=school_others.id,
        from_lyon=False,
        active=True,
        inscription_enabled=True,
        ffsu_id=None,
    )
    await add_object_to_db(school_others_extension)

    global product1, product2, product_old_edition
    product1 = models_sport_competition.CompetitionProduct(
        id=uuid4(),
        name="Product 1",
        description="Description for Product 1",
        edition_id=active_edition.id,
    )
    await add_object_to_db(product1)
    product2 = models_sport_competition.CompetitionProduct(
        id=uuid4(),
        name="Product 2",
        description="Description for Product 2",
        edition_id=active_edition.id,
    )
    await add_object_to_db(product2)
    product_old_edition = models_sport_competition.CompetitionProduct(
        id=uuid4(),
        name="Old Edition Product",
        description="Description for Old Edition Product",
        edition_id=old_edition.id,
    )
    await add_object_to_db(product_old_edition)

    global \
        variant_for_athlete, \
        variant_for_cameraman, \
        variant_for_pompom, \
        variant_for_fanfare, \
        variant_for_volunteer
    variant_for_athlete = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Athlete Variant",
        description="Variant for athletes",
        price=1000,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.athlete,
    )
    await add_object_to_db(variant_for_athlete)
    variant_for_cameraman = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Cameraman Variant",
        description="Variant for cameramen",
        price=500,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.cameraman,
    )
    await add_object_to_db(variant_for_cameraman)
    variant_for_pompom = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Pompom Variant",
        description="Variant for pompom teams",
        price=300,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.pompom,
    )
    await add_object_to_db(variant_for_pompom)
    variant_for_fanfare = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Fanfare Variant",
        description="Variant for fanfare teams",
        price=400,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.fanfare,
    )
    await add_object_to_db(variant_for_fanfare)
    variant_for_volunteer = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Volunteer Variant",
        description="Variant for volunteers",
        price=200,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=ProductPublicType.volunteer,
    )
    await add_object_to_db(variant_for_volunteer)

    global variant_for_centrale, variant_for_from_lyon, variant_for_others
    variant_for_centrale = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product2.id,
        edition_id=active_edition.id,
        name="Centrale Variant",
        description="Variant for Centrale Lyon",
        price=1500,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=None,
    )
    await add_object_to_db(variant_for_centrale)
    variant_for_from_lyon = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product2.id,
        edition_id=active_edition.id,
        name="From Lyon Variant",
        description="Variant for schools from Lyon",
        price=1200,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.from_lyon,
        public_type=None,
    )
    await add_object_to_db(variant_for_from_lyon)
    variant_for_others = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product2.id,
        edition_id=active_edition.id,
        name="Others Variant",
        description="Variant for other schools",
        price=1000,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.others,
        public_type=None,
    )
    await add_object_to_db(variant_for_others)

    global variant_unique, variant_disabled, variant_old_edition

    variant_unique = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Unique Variant",
        description="Variant that can only be purchased once",
        price=2000,
        enabled=True,
        unique=True,
        school_type=ProductSchoolType.centrale,
        public_type=None,
    )
    await add_object_to_db(variant_unique)
    variant_disabled = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product1.id,
        edition_id=active_edition.id,
        name="Disabled Variant",
        description="Variant that is disabled",
        price=1500,
        enabled=False,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=None,
    )
    await add_object_to_db(variant_disabled)
    variant_old_edition = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        product_id=product_old_edition.id,
        edition_id=old_edition.id,
        name="Old Edition Variant",
        description="Variant for old edition products",
        price=1000,
        enabled=True,
        unique=False,
        school_type=ProductSchoolType.centrale,
        public_type=None,
    )
    await add_object_to_db(variant_old_edition)

    global purchase, payment, checkout
    purchase = models_sport_competition.CompetitionPurchase(
        product_variant_id=variant_for_athlete.id,
        user_id=admin_user.id,
        edition_id=active_edition.id,
        quantity=2,
        validated=False,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(purchase)
    payment = models_sport_competition.CompetitionPayment(
        id=uuid4(),
        user_id=admin_user.id,
        edition_id=active_edition.id,
        total=2000,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(payment)
    base_checkout = models_payment.Checkout(
        id=uuid4(),
        module="competition",
        name="Competition Checkout",
        amount=2000,
        hello_asso_checkout_id=1,
        secret="secret",
    )
    checkout = models_sport_competition.CompetitionCheckout(
        id=uuid4(),
        user_id=admin_user.id,
        edition_id=active_edition.id,
        checkout_id=base_checkout.id,
    )
