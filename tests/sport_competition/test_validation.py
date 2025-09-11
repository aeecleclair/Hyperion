from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest_asyncio

from app.core.groups.groups_type import GroupType
from app.core.schools import models_schools
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

school_sport_quota: models_schools.CoreSchool
school_simple_general_quota: models_schools.CoreSchool
school_athlete_general_quota: models_schools.CoreSchool
school_non_athlete_general_quota: models_schools.CoreSchool
school_product_quota: models_schools.CoreSchool
school_no_quota: models_schools.CoreSchool

school_sport_quota_extension: models_sport_competition.SchoolExtension
school_simple_general_quota_extension: models_sport_competition.SchoolExtension
school_athlete_general_quota_extension: models_sport_competition.SchoolExtension
school_non_athlete_general_quota_extension: models_sport_competition.SchoolExtension
school_product_quota_extension: models_sport_competition.SchoolExtension
school_no_quota_extension: models_sport_competition.SchoolExtension


active_edition: models_sport_competition.CompetitionEdition

admin_user: models_users.CoreUser
admin_token: str

athlete_user: models_users.CoreUser
cameraman_user: models_users.CoreUser
pompom_user: models_users.CoreUser
fanfare_user: models_users.CoreUser
volunteer_user: models_users.CoreUser
athlete_cameraman_user: models_users.CoreUser
athlete_pompom_user: models_users.CoreUser
athlete_fanfare_user: models_users.CoreUser

competition_user_admin: models_sport_competition.CompetitionUser
competition_user_athlete: models_sport_competition.CompetitionUser
competition_user_cameraman: models_sport_competition.CompetitionUser
competition_user_pompom: models_sport_competition.CompetitionUser
competition_user_fanfare: models_sport_competition.CompetitionUser
competition_user_volunteer: models_sport_competition.CompetitionUser
competition_user_athlete_cameraman: models_sport_competition.CompetitionUser
competition_user_athlete_pompom: models_sport_competition.CompetitionUser
competition_user_athlete_fanfare: models_sport_competition.CompetitionUser

sport: models_sport_competition.Sport

team_sport_quota_school: models_sport_competition.CompetitionTeam
team_athlete_general_quota_school: models_sport_competition.CompetitionTeam

participant_athlete_user: models_sport_competition.CompetitionParticipant
participant_athlete_cameraman_user: models_sport_competition.CompetitionParticipant
participant_athlete_pompom_user: models_sport_competition.CompetitionParticipant
participant_athlete_fanfare_user: models_sport_competition.CompetitionParticipant

product: models_sport_competition.CompetitionProduct

variant_athlete_user: models_sport_competition.CompetitionProductVariant
variant_cameraman_user: models_sport_competition.CompetitionProductVariant
variant_pompom_user: models_sport_competition.CompetitionProductVariant
variant_fanfare_user: models_sport_competition.CompetitionProductVariant

school_sport_quota_quota: models_sport_competition.SchoolSportQuota
school_simple_general_quota_quota: models_sport_competition.SchoolGeneralQuota
school_athlete_general_quota_quota: models_sport_competition.SchoolGeneralQuota
school_non_athlete_general_quota_quota: models_sport_competition.SchoolGeneralQuota
school_product_quota_quota: models_sport_competition.SchoolProductQuota


async def create_competition_user(
    edition_id: UUID,
    school_id: UUID,
    is_athlete: bool,
    is_cameraman: bool,
    is_pompom: bool,
    is_fanfare: bool,
    is_volunteer: bool,
    sport_category: SportCategory,
) -> tuple[models_users.CoreUser, models_sport_competition.CompetitionUser, str]:
    new_user = await create_user_with_groups(
        [],
        school_id=school_id,
    )
    new_competition_user = models_sport_competition.CompetitionUser(
        user_id=new_user.id,
        edition_id=edition_id,
        sport_category=sport_category,
        created_at=datetime.now(UTC),
        validated=False,
        is_athlete=is_athlete,
        is_cameraman=is_cameraman,
        is_pompom=is_pompom,
        is_fanfare=is_fanfare,
        is_volunteer=is_volunteer,
    )
    await add_object_to_db(new_competition_user)
    token = create_api_access_token(new_user)
    return new_user, new_competition_user, token


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global \
        school_sport_quota, \
        school_simple_general_quota, \
        school_athlete_general_quota, \
        school_non_athlete_general_quota, \
        school_product_quota, \
        school_no_quota

    school_sport_quota = models_schools.CoreSchool(
        id=uuid4(),
        name="Sport Quota School",
        email_regex=".*",
    )
    await add_object_to_db(school_sport_quota)
    school_simple_general_quota = models_schools.CoreSchool(
        id=uuid4(),
        name="Simple General Quota School",
        email_regex=".*",
    )
    await add_object_to_db(school_simple_general_quota)
    school_athlete_general_quota = models_schools.CoreSchool(
        id=uuid4(),
        name="Athlete General Quota School",
        email_regex=".*",
    )
    await add_object_to_db(school_athlete_general_quota)
    school_non_athlete_general_quota = models_schools.CoreSchool(
        id=uuid4(),
        name="Non Athlete General Quota School",
        email_regex=".*",
    )
    await add_object_to_db(school_non_athlete_general_quota)
    school_product_quota = models_schools.CoreSchool(
        id=uuid4(),
        name="Product Quota School",
        email_regex=".*",
    )
    await add_object_to_db(school_product_quota)
    school_no_quota = models_schools.CoreSchool(
        id=uuid4(),
        name="No Quota School",
        email_regex=".*",
    )
    await add_object_to_db(school_no_quota)

    global \
        school_sport_quota_extension, \
        school_simple_general_quota_extension, \
        school_athlete_general_quota_extension, \
        school_non_athlete_general_quota_extension, \
        school_product_quota_extension, \
        school_no_quota_extension
    school_sport_quota_extension = models_sport_competition.SchoolExtension(
        school_id=school_sport_quota.id,
        ffsu_id=None,
        from_lyon=True,
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(school_sport_quota_extension)
    school_simple_general_quota_extension = models_sport_competition.SchoolExtension(
        school_id=school_simple_general_quota.id,
        ffsu_id=None,
        from_lyon=True,
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(school_simple_general_quota_extension)
    school_athlete_general_quota_extension = models_sport_competition.SchoolExtension(
        school_id=school_athlete_general_quota.id,
        ffsu_id=None,
        from_lyon=True,
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(school_athlete_general_quota_extension)
    school_non_athlete_general_quota_extension = (
        models_sport_competition.SchoolExtension(
            school_id=school_non_athlete_general_quota.id,
            ffsu_id=None,
            from_lyon=True,
            active=True,
            inscription_enabled=True,
        )
    )
    await add_object_to_db(school_non_athlete_general_quota_extension)
    school_product_quota_extension = models_sport_competition.SchoolExtension(
        school_id=school_product_quota.id,
        ffsu_id=None,
        from_lyon=True,
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(school_product_quota_extension)
    school_no_quota_extension = models_sport_competition.SchoolExtension(
        school_id=school_no_quota.id,
        ffsu_id=None,
        from_lyon=True,
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(school_no_quota_extension)

    global active_edition
    active_edition = models_sport_competition.CompetitionEdition(
        id=uuid4(),
        year=2024,
        name="Active Edition",
        start_date=datetime(2024, 1, 1, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, tzinfo=UTC),
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(active_edition)

    global \
        admin_user, \
        admin_token, \
        athlete_user, \
        cameraman_user, \
        pompom_user, \
        fanfare_user, \
        volunteer_user, \
        athlete_cameraman_user, \
        athlete_pompom_user, \
        athlete_fanfare_user
    global \
        competition_user_admin, \
        competition_user_athlete, \
        competition_user_cameraman, \
        competition_user_pompom, \
        competition_user_fanfare, \
        competition_user_volunteer, \
        competition_user_athlete_cameraman, \
        competition_user_athlete_pompom, \
        competition_user_athlete_fanfare

    admin_user = await create_user_with_groups(
        [GroupType.admin, GroupType.competition_admin],
    )
    admin_token = create_api_access_token(admin_user)
    competition_user_admin = models_sport_competition.CompetitionUser(
        user_id=admin_user.id,
        edition_id=active_edition.id,
        sport_category=SportCategory.masculine,
        created_at=datetime.now(UTC),
        validated=False,
    )
    await add_object_to_db(competition_user_admin)
    athlete_user, competition_user_athlete, _ = await create_competition_user(
        active_edition.id,
        school_sport_quota.id,
        is_athlete=True,
        is_cameraman=False,
        is_pompom=False,
        is_fanfare=False,
        is_volunteer=False,
        sport_category=SportCategory.masculine,
    )
    cameraman_user, competition_user_cameraman, _ = await create_competition_user(
        active_edition.id,
        school_sport_quota.id,
        is_athlete=False,
        is_cameraman=True,
        is_pompom=False,
        is_fanfare=False,
        is_volunteer=False,
        sport_category=SportCategory.masculine,
    )
    pompom_user, competition_user_pompom, _ = await create_competition_user(
        active_edition.id,
        school_sport_quota.id,
        is_athlete=False,
        is_cameraman=False,
        is_pompom=True,
        is_fanfare=False,
        is_volunteer=False,
        sport_category=SportCategory.feminine,
    )
    fanfare_user, competition_user_fanfare, _ = await create_competition_user(
        active_edition.id,
        school_sport_quota.id,
        is_athlete=False,
        is_cameraman=False,
        is_pompom=False,
        is_fanfare=True,
        is_volunteer=False,
        sport_category=SportCategory.feminine,
    )
    volunteer_user, competition_user_volunteer, _ = await create_competition_user(
        active_edition.id,
        school_sport_quota.id,
        is_athlete=False,
        is_cameraman=False,
        is_pompom=False,
        is_fanfare=False,
        is_volunteer=True,
        sport_category=SportCategory.feminine,
    )
    (
        athlete_cameraman_user,
        competition_user_athlete_cameraman,
        _,
    ) = await create_competition_user(
        active_edition.id,
        school_sport_quota.id,
        is_athlete=True,
        is_cameraman=True,
        is_pompom=False,
        is_fanfare=False,
        is_volunteer=False,
        sport_category=SportCategory.masculine,
    )
    (
        athlete_pompom_user,
        competition_user_athlete_pompom,
        _,
    ) = await create_competition_user(
        active_edition.id,
        school_sport_quota.id,
        is_athlete=True,
        is_cameraman=False,
        is_pompom=True,
        is_fanfare=False,
        is_volunteer=False,
        sport_category=SportCategory.feminine,
    )
    (
        athlete_fanfare_user,
        competition_user_athlete_fanfare,
        _,
    ) = await create_competition_user(
        active_edition.id,
        school_sport_quota.id,
        is_athlete=True,
        is_cameraman=False,
        is_pompom=False,
        is_fanfare=True,
        is_volunteer=False,
        sport_category=SportCategory.feminine,
    )

    global sport
    sport = models_sport_competition.Sport(
        id=uuid4(),
        name="Sport 1",
        active=True,
        sport_category=SportCategory.masculine,
        team_size=4,
        substitute_max=None,
    )
    await add_object_to_db(sport)

    global team_sport_quota_school, team_athlete_general_quota_school
    team_sport_quota_school = models_sport_competition.CompetitionTeam(
        id=uuid4(),
        edition_id=active_edition.id,
        school_id=school_sport_quota.id,
        sport_id=sport.id,
        name="Sport Quota Team",
        created_at=datetime.now(UTC),
        captain_id=athlete_user.id,
    )
    await add_object_to_db(team_sport_quota_school)
    team_athlete_general_quota_school = models_sport_competition.CompetitionTeam(
        id=uuid4(),
        edition_id=active_edition.id,
        school_id=school_athlete_general_quota.id,
        sport_id=sport.id,
        name="Athlete General Quota Team",
        created_at=datetime.now(UTC),
        captain_id=athlete_user.id,
    )
    await add_object_to_db(team_athlete_general_quota_school)

    global \
        participant_athlete_user, \
        participant_athlete_cameraman_user, \
        participant_athlete_pompom_user, \
        participant_athlete_fanfare_user
    participant_athlete_user = models_sport_competition.CompetitionParticipant(
        user_id=athlete_user.id,
        edition_id=active_edition.id,
        school_id=school_sport_quota.id,
        sport_id=sport.id,
        team_id=team_sport_quota_school.id,
        substitute=False,
        license=None,
        is_license_valid=True,
    )
    await add_object_to_db(participant_athlete_user)
    participant_athlete_cameraman_user = (
        models_sport_competition.CompetitionParticipant(
            user_id=athlete_cameraman_user.id,
            edition_id=active_edition.id,
            school_id=school_sport_quota.id,
            sport_id=sport.id,
            team_id=team_sport_quota_school.id,
            substitute=False,
            license=None,
            is_license_valid=True,
        )
    )
    await add_object_to_db(participant_athlete_cameraman_user)
    participant_athlete_pompom_user = models_sport_competition.CompetitionParticipant(
        user_id=athlete_pompom_user.id,
        edition_id=active_edition.id,
        school_id=school_sport_quota.id,
        sport_id=sport.id,
        team_id=team_sport_quota_school.id,
        substitute=False,
        license=None,
        is_license_valid=True,
    )
    await add_object_to_db(participant_athlete_pompom_user)
    participant_athlete_fanfare_user = models_sport_competition.CompetitionParticipant(
        user_id=athlete_fanfare_user.id,
        edition_id=active_edition.id,
        school_id=school_sport_quota.id,
        sport_id=sport.id,
        team_id=team_sport_quota_school.id,
        substitute=False,
        license=None,
        is_license_valid=True,
    )
    await add_object_to_db(participant_athlete_fanfare_user)

    global product
    product = models_sport_competition.CompetitionProduct(
        id=uuid4(),
        edition_id=active_edition.id,
        name="Product 1",
        description="Description 1",
        required=False,
    )
    await add_object_to_db(product)

    global \
        variant_athlete_user, \
        variant_cameraman_user, \
        variant_pompom_user, \
        variant_fanfare_user
    variant_athlete_user = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        edition_id=active_edition.id,
        product_id=product.id,
        name="Athlete Variant",
        price=1000,
        enabled=True,
        unique=True,
        public_type=ProductPublicType.athlete,
        school_type=ProductSchoolType.from_lyon,
    )
    await add_object_to_db(variant_athlete_user)
    variant_cameraman_user = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        edition_id=active_edition.id,
        product_id=product.id,
        name="Cameraman Variant",
        price=2000,
        enabled=True,
        unique=True,
        public_type=ProductPublicType.cameraman,
        school_type=ProductSchoolType.from_lyon,
    )
    await add_object_to_db(variant_cameraman_user)
    variant_pompom_user = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        edition_id=active_edition.id,
        product_id=product.id,
        name="Pompom Variant",
        price=1500,
        enabled=True,
        unique=True,
        public_type=ProductPublicType.pompom,
        school_type=ProductSchoolType.from_lyon,
    )
    await add_object_to_db(variant_pompom_user)
    variant_fanfare_user = models_sport_competition.CompetitionProductVariant(
        id=uuid4(),
        edition_id=active_edition.id,
        product_id=product.id,
        name="Fanfare Variant",
        price=1500,
        enabled=True,
        unique=True,
        public_type=ProductPublicType.fanfare,
        school_type=ProductSchoolType.from_lyon,
    )
    await add_object_to_db(variant_fanfare_user)

    global \
        school_sport_quota_quota, \
        school_simple_general_quota_quota, \
        school_athlete_general_quota_quota, \
        school_non_athlete_general_quota_quota, \
        school_product_quota_quota
    school_sport_quota_quota = models_sport_competition.SchoolSportQuota(
        school_id=school_sport_quota.id,
        edition_id=active_edition.id,
        sport_id=sport.id,
        participant_quota=0,
        team_quota=1,
    )
    await add_object_to_db(school_sport_quota_quota)
    school_simple_general_quota_quota = models_sport_competition.SchoolGeneralQuota(
        school_id=school_simple_general_quota.id,
        edition_id=active_edition.id,
        athlete_quota=0,
        cameraman_quota=0,
        pompom_quota=0,
        fanfare_quota=0,
        athlete_cameraman_quota=10,
        athlete_pompom_quota=10,
        athlete_fanfare_quota=10,
        non_athlete_cameraman_quota=10,
        non_athlete_pompom_quota=10,
        non_athlete_fanfare_quota=10,
    )
    await add_object_to_db(school_simple_general_quota_quota)
    school_athlete_general_quota_quota = models_sport_competition.SchoolGeneralQuota(
        school_id=school_athlete_general_quota.id,
        edition_id=active_edition.id,
        athlete_quota=10,
        cameraman_quota=10,
        pompom_quota=10,
        fanfare_quota=10,
        athlete_cameraman_quota=0,
        athlete_pompom_quota=0,
        athlete_fanfare_quota=0,
        non_athlete_cameraman_quota=10,
        non_athlete_pompom_quota=10,
        non_athlete_fanfare_quota=10,
    )
    await add_object_to_db(school_athlete_general_quota_quota)
    school_non_athlete_general_quota_quota = (
        models_sport_competition.SchoolGeneralQuota(
            school_id=school_non_athlete_general_quota.id,
            edition_id=active_edition.id,
            athlete_quota=10,
            cameraman_quota=10,
            pompom_quota=10,
            fanfare_quota=10,
            athlete_cameraman_quota=10,
            athlete_pompom_quota=10,
            athlete_fanfare_quota=10,
            non_athlete_cameraman_quota=0,
            non_athlete_pompom_quota=0,
            non_athlete_fanfare_quota=0,
        )
    )
    await add_object_to_db(school_non_athlete_general_quota_quota)
    school_product_quota_quota = models_sport_competition.SchoolProductQuota(
        school_id=school_product_quota.id,
        edition_id=active_edition.id,
        product_id=product.id,
        quota=0,
    )
    await add_object_to_db(school_product_quota_quota)
