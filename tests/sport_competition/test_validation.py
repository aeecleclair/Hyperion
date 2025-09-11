from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.core.groups.groups_type import GroupType
from app.core.schools import models_schools
from app.core.users import cruds_users, models_users, schemas_users
from app.modules.sport_competition import (
    cruds_sport_competition,
    models_sport_competition,
)
from app.modules.sport_competition.types_sport_competition import (
    ProductPublicType,
    ProductSchoolType,
    SportCategory,
)
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
    get_TestingSessionLocal,
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
purchase_athlete_user: models_sport_competition.CompetitionPurchase

school_sport_quota_quota: models_sport_competition.SchoolSportQuota
school_simple_general_quota_quota: models_sport_competition.SchoolGeneralQuota
school_athlete_general_quota_quota: models_sport_competition.SchoolGeneralQuota
school_non_athlete_general_quota_quota: models_sport_competition.SchoolGeneralQuota
school_product_quota_quota: models_sport_competition.SchoolProductQuota


@pytest.fixture
def users():
    return {
        "admin": admin_user,
        "athlete": athlete_user,
        "cameraman": cameraman_user,
        "pompom": pompom_user,
        "fanfare": fanfare_user,
        "volunteer": volunteer_user,
        "athlete_cameraman": athlete_cameraman_user,
        "athlete_pompom": athlete_pompom_user,
        "athlete_fanfare": athlete_fanfare_user,
    }


@pytest.fixture
def schools():
    return {
        "school_sport_quota": school_sport_quota,
        "school_simple_general_quota": school_simple_general_quota,
        "school_athlete_general_quota": school_athlete_general_quota,
        "school_non_athlete_general_quota": school_non_athlete_general_quota,
        "school_product_quota": school_product_quota,
        "school_no_quota": school_no_quota,
    }


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
        is_athlete=True,
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
        certificate_file_id=None,
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
            certificate_file_id=None,
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
        certificate_file_id=None,
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
        certificate_file_id=None,
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

    global variant_athlete_user
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

    global purchase_athlete_user
    purchase_athlete_user = models_sport_competition.CompetitionPurchase(
        user_id=athlete_user.id,
        product_variant_id=variant_athlete_user.id,
        edition_id=active_edition.id,
        quantity=1,
        validated=False,
        purchased_on=datetime.now(UTC),
    )
    await add_object_to_db(purchase_athlete_user)

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


@pytest.mark.parametrize(
    ("user", "school", "expected_status_code", "expected_message"),
    [
        (
            "athlete",
            "school_sport_quota",
            400,
            "Participant quota reached",
        ),
        (
            "athlete",
            "school_simple_general_quota",
            400,
            "Athlete quota reached",
        ),
        (
            "cameraman",
            "school_simple_general_quota",
            400,
            "Cameraman quota reached",
        ),
        (
            "pompom",
            "school_simple_general_quota",
            400,
            "Pompom quota reached",
        ),
        (
            "fanfare",
            "school_simple_general_quota",
            400,
            "Fanfare quota reached",
        ),
        (
            "cameraman",
            "school_non_athlete_general_quota",
            400,
            "Non athlete cameraman quota reached",
        ),
        (
            "pompom",
            "school_non_athlete_general_quota",
            400,
            "Non athlete pompom quota reached",
        ),
        (
            "fanfare",
            "school_non_athlete_general_quota",
            400,
            "Non athlete fanfare quota reached",
        ),
        (
            "athlete_cameraman",
            "school_athlete_general_quota",
            400,
            "Athlete cameraman quota reached",
        ),
        (
            "athlete_pompom",
            "school_athlete_general_quota",
            400,
            "Athlete pompom quota reached",
        ),
        (
            "athlete_fanfare",
            "school_athlete_general_quota",
            400,
            "Athlete fanfare quota reached",
        ),
        (
            "athlete",
            "school_product_quota",
            400,
            "Product quota reached",
        ),
        (
            "athlete",
            "school_no_quota",
            204,
            "No Content",
        ),
    ],
)
async def test_validate_competition_user(
    client: TestClient,
    users: dict[str, models_users.CoreUser],
    schools: dict[str, models_schools.CoreSchool],
    user: str,
    school: str,
    expected_status_code: int,
    expected_message: str,
) -> None:
    async with get_TestingSessionLocal()() as db:
        await cruds_users.update_user(
            db,
            users[user].id,
            schemas_users.CoreUserUpdateAdmin(school_id=schools[school].id),
        )
        await db.execute(
            update(models_sport_competition.CompetitionParticipant)
            .where(
                models_sport_competition.CompetitionParticipant.user_id
                == users[user].id,
                models_sport_competition.CompetitionParticipant.edition_id
                == active_edition.id,
            )
            .values(school_id=schools[school].id),
        )
        await db.commit()
    response = client.patch(
        f"/competition/users/{users[user].id}/validate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == expected_status_code
    if expected_status_code != 204:
        assert response.json()["detail"] == expected_message
    async with get_TestingSessionLocal()() as db:
        competition_user = await cruds_sport_competition.load_competition_user_by_id(
            users[user].id,
            active_edition.id,
            db,
        )
        assert competition_user is not None
        if expected_status_code != 204:
            assert competition_user.validated is False
        else:
            assert competition_user.validated is True
