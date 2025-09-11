import uuid
from datetime import UTC, datetime

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.core.schools import models_schools
from app.core.schools.schools_type import SchoolType
from app.core.users import models_users
from app.modules.sport_competition import models_sport_competition
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
    SportCategory,
)
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

school: models_schools.CoreSchool
edition: models_sport_competition.CompetitionEdition

admin_user: models_users.CoreUser
school_bds_user: models_users.CoreUser
sport_manager_user: models_users.CoreUser
user3: models_users.CoreUser
admin_token: str
school_bds_token: str
sport_manager_token: str
user3_token: str

competition_user_admin: models_sport_competition.CompetitionUser
competition_user_school_bds: models_sport_competition.CompetitionUser
competition_user_sport_manager: models_sport_competition.CompetitionUser

ecl_extension: models_sport_competition.SchoolExtension
school_extension: models_sport_competition.SchoolExtension
ecl_general_quota: models_sport_competition.SchoolGeneralQuota
school_general_quota: models_sport_competition.SchoolGeneralQuota

sport_free_quota: models_sport_competition.Sport
sport_used_quota: models_sport_competition.Sport
sport_with_team: models_sport_competition.Sport
sport_with_substitute: models_sport_competition.Sport
ecl_sport_free_quota: models_sport_competition.SchoolSportQuota
ecl_sport_used_quota: models_sport_competition.SchoolSportQuota

team1: models_sport_competition.Team

participant1: models_sport_competition.Participant
participant2: models_sport_competition.Participant


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    for group in CompetitionGroupType:
        group_model = models_sport_competition.CompetitionGroup(
            id=group.value,
            name=group.name,
        )
        await add_object_to_db(group_model)

    global school, edition
    school = models_schools.CoreSchool(
        id=uuid.uuid4(),
        name="Emlyon Business School",
        email_regex=r"^[a-zA-Z0-9._%+-]+@edu.emlyon.fr$",
    )
    await add_object_to_db(school)
    edition = models_sport_competition.CompetitionEdition(
        id=uuid.uuid4(),
        name="Edition 2024",
        year=2024,
        start_date=datetime(2024, 1, 1, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, tzinfo=UTC),
        activated=True,
    )
    await add_object_to_db(edition)

    global admin_user, school_bds_user, sport_manager_user, user3
    admin_user = await create_user_with_groups(
        [GroupType.competition_admin],
    )
    school_bds_user = await create_user_with_groups(
        [],
        school_id=school.id,
    )
    sport_manager_user = await create_user_with_groups(
        [],
    )
    user3 = await create_user_with_groups(
        [],
    )

    global admin_token, school_bds_token, sport_manager_token, user3_token
    admin_token = create_api_access_token(admin_user)
    school_bds_token = create_api_access_token(school_bds_user)
    sport_manager_token = create_api_access_token(sport_manager_user)
    user3_token = create_api_access_token(user3)

    global \
        competition_user_admin, \
        competition_user_school_bds, \
        competition_user_sport_manager
    competition_user_admin = models_sport_competition.CompetitionUser(
        user_id=admin_user.id,
        sport_category=SportCategory.masculine,
    )
    await add_object_to_db(competition_user_admin)
    competition_user_school_bds = models_sport_competition.CompetitionUser(
        user_id=school_bds_user.id,
        sport_category=SportCategory.masculine,
    )
    await add_object_to_db(competition_user_school_bds)
    competition_user_sport_manager = models_sport_competition.CompetitionUser(
        user_id=sport_manager_user.id,
        sport_category=SportCategory.masculine,
    )
    await add_object_to_db(competition_user_sport_manager)
    user1_bds_membership = models_sport_competition.EditionGroupMembership(
        user_id=school_bds_user.id,
        edition_id=edition.id,
        group_id=CompetitionGroupType.schools_bds.value,
    )
    await add_object_to_db(user1_bds_membership)
    user2_sport_manager_membership = models_sport_competition.EditionGroupMembership(
        user_id=sport_manager_user.id,
        edition_id=edition.id,
        group_id=CompetitionGroupType.sport_manager.value,
    )
    await add_object_to_db(user2_sport_manager_membership)

    global ecl_extension, school_extension
    ecl_extension = models_sport_competition.SchoolExtension(
        school_id=SchoolType.centrale_lyon.value,
        from_lyon=True,
        activated=True,
    )
    await add_object_to_db(ecl_extension)
    school_extension = models_sport_competition.SchoolExtension(
        school_id=school.id,
        from_lyon=False,
        activated=True,
    )
    await add_object_to_db(school_extension)

    global ecl_general_quota, school_general_quota
    ecl_general_quota = models_sport_competition.SchoolGeneralQuota(
        school_id=SchoolType.centrale_lyon.value,
        edition_id=edition.id,
        athlete_quota=None,
        cameraman_quota=None,
        pompom_quota=None,
        fanfare_quota=None,
        non_athlete_quota=None,
    )
    await add_object_to_db(ecl_general_quota)
    school_general_quota = models_sport_competition.SchoolGeneralQuota(
        school_id=school.id,
        edition_id=edition.id,
        athlete_quota=1,
        cameraman_quota=1,
        pompom_quota=1,
        fanfare_quota=1,
        non_athlete_quota=1,
    )
    await add_object_to_db(school_general_quota)

    global sport_free_quota, sport_used_quota, sport_with_team, sport_with_substitute
    sport_free_quota = models_sport_competition.Sport(
        id=uuid.uuid4(),
        name="Free Quota Sport",
        team_size=1,
        substitute_max=0,
        activated=True,
        sport_category=None,
    )
    await add_object_to_db(sport_free_quota)
    sport_used_quota = models_sport_competition.Sport(
        id=uuid.uuid4(),
        name="Used Quota Sport",
        team_size=1,
        substitute_max=0,
        activated=True,
        sport_category=None,
    )
    await add_object_to_db(sport_used_quota)
    sport_with_team = models_sport_competition.Sport(
        id=uuid.uuid4(),
        name="Sport with Team",
        team_size=5,
        substitute_max=0,
        activated=True,
        sport_category=None,
    )
    await add_object_to_db(sport_with_team)
    sport_with_substitute = models_sport_competition.Sport(
        id=uuid.uuid4(),
        name="Sport with Substitute",
        team_size=5,
        substitute_max=2,
        activated=True,
        sport_category=None,
    )
    await add_object_to_db(sport_with_substitute)

    global ecl_sport_free_quota, ecl_sport_used_quota
    ecl_sport_free_quota = models_sport_competition.SchoolSportQuota(
        school_id=school.id,
        edition_id=edition.id,
        sport_id=sport_free_quota.id,
        participant_quota=2,
        team_quota=1,
    )
    await add_object_to_db(ecl_sport_free_quota)
    ecl_sport_used_quota = models_sport_competition.SchoolSportQuota(
        school_id=school.id,
        edition_id=edition.id,
        sport_id=sport_used_quota.id,
        participant_quota=0,
        team_quota=1,
    )
    await add_object_to_db(ecl_sport_used_quota)

    global team1
    team1 = models_sport_competition.Team(
        id=uuid.uuid4(),
        sport_id=sport_with_team.id,
        school_id=SchoolType.centrale_lyon.value,
        edition_id=edition.id,
        name="Team 1",
        captain_id=sport_manager_user.id,
    )
    await add_object_to_db(team1)

    global participant1, participant2
    participant1 = models_sport_competition.Participant(
        user_id=admin_user.id,
        school_id=SchoolType.centrale_lyon.value,
        edition_id=edition.id,
        sport_id=sport_free_quota.id,
        team_id=None,
        substitute=False,
        license="1234567890",
        validated=True,
    )
    await add_object_to_db(participant1)
    participant2 = models_sport_competition.Participant(
        user_id=sport_manager_user.id,
        school_id=SchoolType.centrale_lyon.value,
        edition_id=edition.id,
        sport_id=sport_with_team.id,
        team_id=team1.id,
        substitute=False,
        license="0987654321",
        validated=True,
    )
    await add_object_to_db(participant2)


async def test_create_sport_competition_as_admin(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/editions/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "New Competition Edition",
            "year": 2025,
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-12-31T23:59:59Z",
        },
    )
    assert response.status_code == 201, response.json()
    editions = client.get(
        "/competition/editions/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert editions.status_code == 200
    editions_json = editions.json()
    new_edition = next(
        (
            edition
            for edition in editions_json
            if edition["name"] == "New Competition Edition" and edition["year"] == 2025
        ),
        None,
    )
    assert new_edition is not None


async def test_create_sport_competition_as_random(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/editions/",
        headers={"Authorization": f"Bearer {school_bds_token}"},
        json={
            "name": "Unauthorized Edition",
            "year": 2025,
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-12-31T23:59:59Z",
        },
    )
    assert response.status_code == 403, response.json()

    editions = client.get(
        "/competition/editions/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert editions.status_code == 200
    editions_json = editions.json()
    unauthorized_edition = next(
        (
            edition
            for edition in editions_json
            if edition["name"] == "Unauthorized Edition" and edition["year"] == 2025
        ),
        None,
    )
    assert unauthorized_edition is None
