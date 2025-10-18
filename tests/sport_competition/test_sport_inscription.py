from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete, update

from app.core.groups.groups_type import GroupType
from app.core.schools import models_schools
from app.core.schools.schools_type import SchoolType
from app.core.users import models_users
from app.modules.sport_competition import models_sport_competition
from app.modules.sport_competition.schemas_sport_competition import (
    LocationBase,
    MatchBase,
    ParticipantInfo,
    SportPodiumRankings,
    TeamInfo,
    TeamSportResultBase,
    VolunteerShiftBase,
)
from app.modules.sport_competition.types_sport_competition import (
    CompetitionGroupType,
    SportCategory,
)
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
    get_TestingSessionLocal,
)

school1: models_schools.CoreSchool
school2: models_schools.CoreSchool

active_edition: models_sport_competition.CompetitionEdition
old_edition: models_sport_competition.CompetitionEdition

admin_user: models_users.CoreUser
school_bds_user: models_users.CoreUser
sport_manager_user: models_users.CoreUser
user3: models_users.CoreUser
user4: models_users.CoreUser
admin_token: str
school_bds_token: str
sport_manager_token: str
user3_token: str
user4_token: str

competition_user_admin: models_sport_competition.CompetitionUser
competition_user_school_bds: models_sport_competition.CompetitionUser
competition_user_sport_manager: models_sport_competition.CompetitionUser

ecl_extension: models_sport_competition.SchoolExtension
school1_extension: models_sport_competition.SchoolExtension
ecl_general_quota: models_sport_competition.SchoolGeneralQuota
school_general_quota: models_sport_competition.SchoolGeneralQuota

sport_free_quota: models_sport_competition.Sport
sport_used_quota: models_sport_competition.Sport
sport_with_team: models_sport_competition.Sport
sport_with_substitute: models_sport_competition.Sport
sport_feminine: models_sport_competition.Sport
ecl_sport_free_quota: models_sport_competition.SchoolSportQuota
ecl_sport_used_quota: models_sport_competition.SchoolSportQuota

team_admin_user: models_sport_competition.CompetitionTeam
team1: models_sport_competition.CompetitionTeam
team2: models_sport_competition.CompetitionTeam

participant1: models_sport_competition.CompetitionParticipant
participant2: models_sport_competition.CompetitionParticipant
participant3: models_sport_competition.CompetitionParticipant

location: models_sport_competition.MatchLocation

match1: models_sport_competition.Match

podium_sport_free_quota: list[models_sport_competition.SportPodium]
podium_sport_with_team: list[models_sport_competition.SportPodium]

volunteer_shift: models_sport_competition.VolunteerShift
volunteer_registration: models_sport_competition.VolunteerRegistration


async def create_competition_user(
    edition_id: UUID,
    school_id: UUID,
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
        is_athlete=True,
    )
    await add_object_to_db(new_competition_user)
    token = create_api_access_token(new_user)
    return new_user, new_competition_user, token


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global school1, school2, active_edition, old_edition
    school1 = models_schools.CoreSchool(
        id=uuid4(),
        name="Emlyon Business School",
        email_regex=r"^[\w.-]+@edu.emlyon.fr$",
    )
    await add_object_to_db(school1)
    school2 = models_schools.CoreSchool(
        id=uuid4(),
        name="Centrale Supelec",
        email_regex=r"^[\w.-]+@edu.centralesupelec.fr$",
    )
    await add_object_to_db(school2)
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

    global admin_user, school_bds_user, sport_manager_user, user3, user4
    admin_user = await create_user_with_groups(
        [GroupType.competition_admin],
        email="Admin User",
    )
    school_bds_user = await create_user_with_groups(
        [],
        email="School BDS User",
        school_id=school1.id,
    )
    sport_manager_user = await create_user_with_groups(
        [],
        email="Sport Manager User",
    )
    user3 = await create_user_with_groups(
        [],
        email="Random User",
    )
    user4 = await create_user_with_groups(
        [],
        email="Another Random User",
    )

    global admin_token, school_bds_token, sport_manager_token, user3_token, user4_token
    admin_token = create_api_access_token(admin_user)
    school_bds_token = create_api_access_token(school_bds_user)
    sport_manager_token = create_api_access_token(sport_manager_user)
    user3_token = create_api_access_token(user3)
    user4_token = create_api_access_token(user4)

    global \
        competition_user_admin, \
        competition_user_school_bds, \
        competition_user_sport_manager
    competition_user_admin = models_sport_competition.CompetitionUser(
        user_id=admin_user.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        is_volunteer=True,
        validated=True,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_admin)
    competition_user_school_bds = models_sport_competition.CompetitionUser(
        user_id=school_bds_user.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        is_pompom=True,
        validated=True,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_school_bds)
    competition_user_sport_manager = models_sport_competition.CompetitionUser(
        user_id=sport_manager_user.id,
        sport_category=SportCategory.masculine,
        edition_id=active_edition.id,
        is_athlete=True,
        is_cameraman=True,
        validated=True,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(competition_user_sport_manager)
    user1_bds_membership = models_sport_competition.CompetitionGroupMembership(
        user_id=school_bds_user.id,
        edition_id=active_edition.id,
        group=CompetitionGroupType.schools_bds,
    )
    await add_object_to_db(user1_bds_membership)
    user2_sport_manager_membership = (
        models_sport_competition.CompetitionGroupMembership(
            user_id=sport_manager_user.id,
            edition_id=active_edition.id,
            group=CompetitionGroupType.sport_manager,
        )
    )
    await add_object_to_db(user2_sport_manager_membership)
    user4_sport_manager_membership = (
        models_sport_competition.CompetitionGroupMembership(
            user_id=user4.id,
            edition_id=active_edition.id,
            group=CompetitionGroupType.sport_manager,
        )
    )
    await add_object_to_db(user4_sport_manager_membership)

    global ecl_extension, school1_extension
    ecl_extension = models_sport_competition.SchoolExtension(
        school_id=SchoolType.centrale_lyon.value,
        from_lyon=True,
        active=True,
        inscription_enabled=False,
    )
    await add_object_to_db(ecl_extension)
    school1_extension = models_sport_competition.SchoolExtension(
        school_id=school1.id,
        from_lyon=False,
        active=False,
        inscription_enabled=False,
    )
    await add_object_to_db(school1_extension)

    global ecl_general_quota, school_general_quota
    ecl_general_quota = models_sport_competition.SchoolGeneralQuota(
        school_id=SchoolType.centrale_lyon.value,
        edition_id=active_edition.id,
        athlete_quota=None,
        cameraman_quota=None,
        pompom_quota=None,
        fanfare_quota=None,
        athlete_cameraman_quota=None,
        athlete_pompom_quota=None,
        athlete_fanfare_quota=None,
        non_athlete_cameraman_quota=None,
        non_athlete_pompom_quota=None,
        non_athlete_fanfare_quota=None,
    )
    await add_object_to_db(ecl_general_quota)
    school_general_quota = models_sport_competition.SchoolGeneralQuota(
        school_id=school1.id,
        edition_id=active_edition.id,
        athlete_quota=1,
        cameraman_quota=1,
        pompom_quota=1,
        fanfare_quota=1,
        athlete_cameraman_quota=1,
        athlete_pompom_quota=1,
        athlete_fanfare_quota=1,
        non_athlete_cameraman_quota=1,
        non_athlete_pompom_quota=1,
        non_athlete_fanfare_quota=1,
    )
    await add_object_to_db(school_general_quota)

    global \
        sport_free_quota, \
        sport_used_quota, \
        sport_with_team, \
        sport_with_substitute, \
        sport_feminine
    sport_free_quota = models_sport_competition.Sport(
        id=uuid4(),
        name="Free Quota Sport",
        team_size=1,
        substitute_max=0,
        active=True,
        sport_category=None,
    )
    await add_object_to_db(sport_free_quota)
    sport_used_quota = models_sport_competition.Sport(
        id=uuid4(),
        name="Used Quota Sport",
        team_size=1,
        substitute_max=0,
        active=True,
        sport_category=None,
    )
    await add_object_to_db(sport_used_quota)
    sport_with_team = models_sport_competition.Sport(
        id=uuid4(),
        name="Sport with Team",
        team_size=5,
        substitute_max=0,
        active=True,
        sport_category=None,
    )
    await add_object_to_db(sport_with_team)
    sport_with_substitute = models_sport_competition.Sport(
        id=uuid4(),
        name="Sport with Substitute",
        team_size=5,
        substitute_max=2,
        active=True,
        sport_category=None,
    )
    await add_object_to_db(sport_with_substitute)
    sport_feminine = models_sport_competition.Sport(
        id=uuid4(),
        name="Feminine Sport",
        team_size=5,
        substitute_max=2,
        active=True,
        sport_category=SportCategory.feminine,
    )
    await add_object_to_db(sport_feminine)

    global ecl_sport_free_quota, ecl_sport_used_quota
    ecl_sport_free_quota = models_sport_competition.SchoolSportQuota(
        school_id=school1.id,
        edition_id=active_edition.id,
        sport_id=sport_free_quota.id,
        participant_quota=2,
        team_quota=1,
    )
    await add_object_to_db(ecl_sport_free_quota)
    ecl_sport_used_quota = models_sport_competition.SchoolSportQuota(
        school_id=school1.id,
        edition_id=active_edition.id,
        sport_id=sport_used_quota.id,
        participant_quota=0,
        team_quota=1,
    )
    await add_object_to_db(ecl_sport_used_quota)

    global team1, team2, team_admin_user
    team1 = models_sport_competition.CompetitionTeam(
        id=uuid4(),
        sport_id=sport_with_team.id,
        school_id=SchoolType.centrale_lyon.value,
        edition_id=active_edition.id,
        name="Team 1",
        captain_id=sport_manager_user.id,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(team1)
    team2 = models_sport_competition.CompetitionTeam(
        id=uuid4(),
        sport_id=sport_with_team.id,
        school_id=school1.id,
        edition_id=active_edition.id,
        name="Team 2",
        captain_id=school_bds_user.id,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(team2)
    team_admin_user = models_sport_competition.CompetitionTeam(
        id=uuid4(),
        sport_id=sport_free_quota.id,
        school_id=SchoolType.centrale_lyon.value,
        edition_id=active_edition.id,
        name="Admin Team",
        captain_id=admin_user.id,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(team_admin_user)

    global participant1, participant2, participant3
    participant1 = models_sport_competition.CompetitionParticipant(
        user_id=admin_user.id,
        school_id=SchoolType.centrale_lyon.value,
        edition_id=active_edition.id,
        sport_id=sport_free_quota.id,
        team_id=team_admin_user.id,
        substitute=False,
        license="1234567890",
        certificate_file_id=None,
        is_license_valid=True,
    )
    await add_object_to_db(participant1)
    participant2 = models_sport_competition.CompetitionParticipant(
        user_id=sport_manager_user.id,
        school_id=SchoolType.centrale_lyon.value,
        edition_id=active_edition.id,
        sport_id=sport_with_team.id,
        team_id=team1.id,
        substitute=False,
        license="0987654321",
        certificate_file_id=None,
        is_license_valid=True,
    )
    await add_object_to_db(participant2)
    (
        participant3_user,
        _,
        _,
    ) = await create_competition_user(
        edition_id=active_edition.id,
        school_id=school1.id,
        sport_category=SportCategory.masculine,
    )
    participant3 = models_sport_competition.CompetitionParticipant(
        user_id=participant3_user.id,
        school_id=SchoolType.centrale_lyon.value,
        edition_id=active_edition.id,
        sport_id=sport_with_team.id,
        team_id=team1.id,
        substitute=False,
        license="1122334455",
        certificate_file_id=None,
        is_license_valid=True,
    )
    await add_object_to_db(participant3)

    global location
    location = models_sport_competition.MatchLocation(
        id=uuid4(),
        edition_id=active_edition.id,
        name="Main Stadium",
        address="123 Main St, City, Country",
        latitude=45.764043,
        longitude=4.835659,
        description="Main stadium for the competition",
    )
    await add_object_to_db(location)

    global match1
    match1 = models_sport_competition.Match(
        id=uuid4(),
        edition_id=active_edition.id,
        sport_id=sport_with_team.id,
        name="Match 1",
        team1_id=team1.id,
        team2_id=team2.id,
        location_id=location.id,
        date=datetime(2024, 6, 15, 15, 0, tzinfo=UTC),
        score_team1=None,
        score_team2=None,
        winner_id=None,
    )
    await add_object_to_db(match1)

    global podium_sport_free_quota, podium_sport_with_team
    podium_sport_with_team = [
        models_sport_competition.SportPodium(
            school_id=SchoolType.centrale_lyon.value,
            edition_id=active_edition.id,
            sport_id=sport_with_team.id,
            rank=1,
            team_id=team_admin_user.id,
            points=10,
        ),
        models_sport_competition.SportPodium(
            school_id=SchoolType.centrale_lyon.value,
            edition_id=active_edition.id,
            sport_id=sport_with_team.id,
            rank=2,
            team_id=team1.id,
            points=5,
        ),
        models_sport_competition.SportPodium(
            school_id=school1.id,
            edition_id=active_edition.id,
            sport_id=sport_with_team.id,
            rank=3,
            team_id=team2.id,
            points=2,
        ),
    ]
    await add_object_to_db(podium_sport_with_team[0])
    await add_object_to_db(podium_sport_with_team[1])
    await add_object_to_db(podium_sport_with_team[2])
    podium_sport_free_quota = [
        models_sport_competition.SportPodium(
            school_id=SchoolType.centrale_lyon.value,
            edition_id=active_edition.id,
            sport_id=sport_free_quota.id,
            rank=1,
            team_id=team_admin_user.id,
            points=10,
        ),
        models_sport_competition.SportPodium(
            school_id=SchoolType.centrale_lyon.value,
            edition_id=active_edition.id,
            sport_id=sport_free_quota.id,
            rank=2,
            team_id=team1.id,
            points=5,
        ),
        models_sport_competition.SportPodium(
            school_id=school1.id,
            edition_id=active_edition.id,
            sport_id=sport_free_quota.id,
            rank=3,
            team_id=team2.id,
            points=2,
        ),
    ]
    await add_object_to_db(podium_sport_free_quota[0])
    await add_object_to_db(podium_sport_free_quota[1])
    await add_object_to_db(podium_sport_free_quota[2])

    global volunteer_shift, volunteer_registration
    volunteer_shift = models_sport_competition.VolunteerShift(
        id=uuid4(),
        edition_id=active_edition.id,
        name="Morning Shift",
        description="Help with setup and registration",
        value=2,
        start_time=datetime(2024, 6, 15, 8, 0, tzinfo=UTC),
        end_time=datetime(2024, 6, 15, 12, 0, tzinfo=UTC),
        location="Main Entrance",
        max_volunteers=1,
    )
    await add_object_to_db(volunteer_shift)
    volunteer_registration = models_sport_competition.VolunteerRegistration(
        user_id=admin_user.id,
        shift_id=volunteer_shift.id,
        edition_id=active_edition.id,
        registered_at=datetime.now(UTC),
        validated=False,
    )
    await add_object_to_db(volunteer_registration)


# region: Sports


async def test_get_sports(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/sports",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    editions = response.json()
    assert len(editions) > 0


async def test_create_sport_as_random(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/sports",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "name": "Unauthorized Sport",
            "team_size": 5,
            "substitute_max": 2,
            "active": True,
            "sport_category": SportCategory.masculine.value,
        },
    )
    assert response.status_code == 403, response.json()

    sports = client.get(
        "/competition/sports",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sports.status_code == 200, sports.json()
    sports_json = sports.json()
    unauthorized_sport = next(
        (s for s in sports_json if s["name"] == "Unauthorized Sport"),
        None,
    )
    assert unauthorized_sport is None


async def test_create_sport_as_admin(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/sports",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "New Sport",
            "team_size": 5,
            "substitute_max": 2,
            "active": True,
            "sport_category": SportCategory.masculine.value,
        },
    )
    assert response.status_code == 201, response.json()
    sport = response.json()

    sports = client.get(
        "/competition/sports",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sports.status_code == 200, sports.json()
    sports_json = sports.json()
    new_sport = next(
        (s for s in sports_json if s["id"] == sport["id"]),
        None,
    )
    assert new_sport is not None


async def test_create_sport_with_invalid_data(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/sports",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Invalid Sport",
            "team_size": -1,  # Invalid team size
            "substitute_max": 2,
            "active": True,
            "sport_category": SportCategory.masculine.value,
        },
    )
    assert response.status_code == 422, response.json()


async def test_create_sport_with_duplicate_name(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/sports",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": sport_free_quota.name,  # Duplicate name
            "team_size": 5,
            "substitute_max": 2,
            "active": True,
            "sport_category": SportCategory.masculine.value,
        },
    )
    assert response.status_code == 400, response.json()


async def test_patch_sport_as_random(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/sports/{sport_free_quota.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "name": "Unauthorized Update",
            "team_size": 6,
            "substitute_max": 3,
            "active": True,
            "sport_category": SportCategory.feminine.value,
        },
    )
    assert response.status_code == 403, response.json()

    sports = client.get(
        "/competition/sports",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sports.status_code == 200, sports.json()
    sports_json = sports.json()
    updated_sport_check = next(
        (s for s in sports_json if s["id"] == str(sport_free_quota.id)),
        None,
    )
    assert updated_sport_check is not None
    assert updated_sport_check["name"] == sport_free_quota.name


async def test_patch_sport_as_admin(
    client: TestClient,
) -> None:
    sport_to_modify = models_sport_competition.Sport(
        id=uuid4(),
        name="Sport to Modify",
        team_size=5,
        substitute_max=2,
        active=True,
        sport_category=SportCategory.masculine,
    )
    await add_object_to_db(sport_to_modify)
    response = client.patch(
        f"/competition/sports/{sport_to_modify.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Updated Sport",
            "team_size": 6,
            "substitute_max": 3,
            "active": True,
            "sport_category": SportCategory.feminine.value,
        },
    )
    assert response.status_code == 204, response.json()

    sports = client.get(
        "/competition/sports",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sports.status_code == 200, sports.json()
    sports_json = sports.json()
    updated_sport_check = next(
        (s for s in sports_json if s["id"] == str(sport_to_modify.id)),
        None,
    )
    assert updated_sport_check is not None
    assert updated_sport_check["name"] == "Updated Sport"


async def test_patch_sport_with_duplicate_name(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/sports/{sport_free_quota.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": sport_used_quota.name,  # Duplicate name
            "team_size": 6,
            "substitute_max": 3,
            "active": True,
            "sport_category": SportCategory.masculine.value,
        },
    )
    assert response.status_code == 400, response.json()


async def test_delete_sport_as_random(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/sports/{sport_free_quota.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()

    sports = client.get(
        "/competition/sports",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sports.status_code == 200, sports.json()
    sports_json = sports.json()
    deleted_sport_check = next(
        (s for s in sports_json if s["id"] == str(sport_free_quota.id)),
        None,
    )
    assert deleted_sport_check is not None, sports.json()


async def test_delete_sport_active(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400, response.json()


async def test_delete_sport_as_admin(
    client: TestClient,
) -> None:
    sport_to_delete = models_sport_competition.Sport(
        id=uuid4(),
        name="Sport to Delete",
        team_size=5,
        substitute_max=2,
        active=False,
        sport_category=SportCategory.masculine,
    )
    await add_object_to_db(sport_to_delete)

    response = client.delete(
        f"/competition/sports/{sport_to_delete.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204, response.json()

    sports = client.get(
        "/competition/sports",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sports.status_code == 200, sports.json()
    sports_json = sports.json()
    deleted_sport_check = next(
        (s for s in sports_json if s["id"] == str(sport_to_delete.id)),
        None,
    )
    assert deleted_sport_check is None


# endregion
# region: Editions


async def test_get_editions(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/editions",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    editions = response.json()
    assert len(editions) > 0


async def test_get_active_edition(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/editions/active",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    edition_data = response.json()
    assert edition_data["id"] == str(active_edition.id)


async def test_create_edition_as_admin(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/editions",
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
        "/competition/editions",
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


async def test_create_edition_as_random(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/editions",
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
        "/competition/editions",
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


async def test_patch_edition_as_admin(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/editions/{old_edition.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Updated Edition",
        },
    )
    assert response.status_code == 204, response.json()

    editions = client.get(
        "/competition/editions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert editions.status_code == 200
    editions_json = editions.json()
    updated_edition = next(
        (edition for edition in editions_json if edition["id"] == str(old_edition.id)),
        None,
    )
    assert updated_edition is not None
    assert updated_edition["name"] == "Updated Edition"


async def test_activate_edition(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/editions/{old_edition.id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204, response.json()
    editions = client.get(
        "/competition/editions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert editions.status_code == 200
    editions_json = editions.json()
    activated_edition = next(
        (edition for edition in editions_json if edition["id"] == str(old_edition.id)),
        None,
    )
    assert activated_edition is not None
    assert activated_edition["active"] is True
    client.post(
        f"/competition/editions/{active_edition.id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )


async def test_enable_inscription_not_active(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/editions/{old_edition.id}/inscription",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=True,
    )
    assert response.status_code == 400, response.json()
    editions = client.get(
        "/competition/editions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert editions.status_code == 200
    editions_json = editions.json()
    enabled_edition = next(
        (edition for edition in editions_json if edition["id"] == str(old_edition.id)),
        None,
    )
    assert enabled_edition is not None
    assert enabled_edition["inscription_enabled"] is False


async def test_enable_inscription(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/editions/{active_edition.id}/inscription",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=True,
    )
    assert response.status_code == 204, response.json()
    editions = client.get(
        "/competition/editions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert editions.status_code == 200
    editions_json = editions.json()
    enabled_edition = next(
        (
            edition
            for edition in editions_json
            if edition["id"] == str(active_edition.id)
        ),
        None,
    )
    assert enabled_edition is not None
    assert enabled_edition["inscription_enabled"] is True, enabled_edition


async def test_patch_edition_as_random(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/editions/{active_edition.id}",
        headers={"Authorization": f"Bearer {school_bds_token}"},
        json={
            "name": "Unauthorized Edition Update",
        },
    )
    assert response.status_code == 403, response.json()

    editions = client.get(
        "/competition/editions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert editions.status_code == 200
    editions_json = editions.json()
    updated_edition_check = next(
        (
            edition
            for edition in editions_json
            if edition["id"] == str(active_edition.id)
        ),
        None,
    )
    assert updated_edition_check is not None
    assert updated_edition_check["name"] == active_edition.name


# endregion
# region: Schools


async def test_get_schools(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/schools",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    schools = response.json()
    assert len(schools) > 0
    assert any(school["school_id"] == str(school1.id) for school in schools)


async def test_post_school_extension_as_random(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/schools",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "school_id": str(school2.id),
            "from_lyon": False,
            "active": True,
            "inscription_enabled": False,
        },
    )
    assert response.status_code == 403, response.json()

    schools = client.get(
        "/competition/schools",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert schools.status_code == 200, schools.json()
    schools_json = schools.json()
    unauthorized_school = next(
        (s for s in schools_json if s["school_id"] == str(school2.id)),
        None,
    )
    assert unauthorized_school is None, schools_json


async def test_post_school_extension_as_admin(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/schools",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "school_id": str(school2.id),
            "from_lyon": False,
            "active": True,
            "inscription_enabled": True,
        },
    )
    assert response.status_code == 201, response.json()

    schools = client.get(
        "/competition/schools",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert schools.status_code == 200, schools.json()
    schools_json = schools.json()
    new_school_extension = next(
        (s for s in schools_json if s["school_id"] == str(school2.id)),
        None,
    )
    assert new_school_extension is not None, schools_json


async def test_patch_school_extension_as_random(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/schools/{school1.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "from_lyon": False,
            "active": True,
            "inscription_enabled": True,
        },
    )
    assert response.status_code == 403, response.json()

    schools = client.get(
        "/competition/schools",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert schools.status_code == 200, schools.json()
    schools_json = schools.json()
    updated_school = next(
        (s for s in schools_json if s["school_id"] == str(school1.id)),
        None,
    )
    assert updated_school is not None
    assert updated_school["from_lyon"] is False
    assert updated_school["active"] is False
    assert updated_school["inscription_enabled"] is False


async def test_patch_school_extension_as_admin(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/schools/{school1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "from_lyon": True,
            "active": True,
            "inscription_enabled": True,
        },
    )
    assert response.status_code == 204, response.json()

    schools = client.get(
        "/competition/schools",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert schools.status_code == 200, schools.json()
    schools_json = schools.json()
    updated_school = next(
        (s for s in schools_json if s["school_id"] == str(school1.id)),
        None,
    )
    assert updated_school is not None
    assert updated_school["from_lyon"] is True
    assert updated_school["active"] is True
    assert updated_school["inscription_enabled"] is True


# endregion
# region: Competition Users


async def test_get_competition_users(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/users",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    users = response.json()
    assert len(users) > 0
    assert all(user["edition_id"] == str(active_edition.id) for user in users)


async def test_get_competition_users_by_school(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/users/schools/{school1.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    users = response.json()
    assert len(users) > 0
    assert all(user["edition_id"] == str(active_edition.id) for user in users)
    assert all(user["user"]["school_id"] == str(school1.id) for user in users)


async def test_get_competition_user_by_id(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/users/{competition_user_admin.user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.json()
    user = response.json()
    assert user["user_id"] == str(competition_user_admin.user_id)
    assert user["edition_id"] == str(competition_user_admin.edition_id)
    assert competition_user_admin.sport_category is not None
    assert user["sport_category"] == competition_user_admin.sport_category.value


async def test_post_competition_user(
    client: TestClient,
) -> None:
    response = client.post(
        "/competition/users",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "sport_category": SportCategory.masculine.value,
            "is_athlete": True,
        },
    )
    assert response.status_code == 201, response.json()
    user = response.json()
    assert user["user_id"] == str(user3.id)
    assert user["edition_id"] == str(active_edition.id)
    assert user["sport_category"] == SportCategory.masculine.value


async def test_patch_competition_user_as_me(
    client: TestClient,
) -> None:
    response = client.patch(
        "/competition/users/me",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "sport_category": SportCategory.feminine.value,
        },
    )
    assert response.status_code == 204, response.json()

    user_response = client.get(
        "/competition/users/me",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert user_response.status_code == 200, user_response.json()
    user = user_response.json()
    assert user["sport_category"] == SportCategory.feminine.value


async def test_patch_competition_user_as_admin(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/users/{competition_user_admin.user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "sport_category": SportCategory.masculine.value,
        },
    )
    assert response.status_code == 204, response.json()

    user_response = client.get(
        f"/competition/users/{competition_user_admin.user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert user_response.status_code == 200, user_response.json()
    user = user_response.json()
    assert user["sport_category"] == SportCategory.masculine.value


# endregion
# region: Competition Groups


async def test_add_user_to_group_as_random(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/groups/{CompetitionGroupType.schools_bds.value}/users/{competition_user_admin.user_id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()

    user = client.get(
        f"/competition/users/{competition_user_admin.user_id}/groups",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert user.status_code == 200, user.json()
    user_json = user.json()
    assert CompetitionGroupType.schools_bds.value not in [
        group["group"] for group in user_json
    ], user_json


async def test_add_user_to_group_as_admin(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/groups/{CompetitionGroupType.schools_bds.value}/users/{competition_user_admin.user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201, response.json()

    user = client.get(
        "/competition/users/me/groups",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert user.status_code == 200, user.json()
    user_json = user.json()
    assert CompetitionGroupType.schools_bds.value in [
        group["group"] for group in user_json
    ], user_json


async def test_remove_user_from_group_as_random(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/groups/{CompetitionGroupType.schools_bds.value}/users/{competition_user_school_bds.user_id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()

    user = client.get(
        f"/competition/users/{competition_user_school_bds.user_id}/groups",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert user.status_code == 200, user.json()
    user_json = user.json()
    assert CompetitionGroupType.schools_bds.value in [
        group["group"] for group in user_json
    ], user_json


# endregion
# region: School General Quotas


async def test_get_school_general_quota_as_random(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/schools/{school1.id}/general-quota",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()


async def test_get_school_general_quota(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/schools/{school1.id}/general-quota",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.json()
    school_quota_json = response.json()
    assert school_quota_json["athlete_quota"] == 1, school_quota_json
    assert school_quota_json["cameraman_quota"] == 1, school_quota_json
    assert school_quota_json["pompom_quota"] == 1, school_quota_json
    assert school_quota_json["fanfare_quota"] == 1, school_quota_json


async def test_get_school_general_quota_as_bds(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/schools/{school1.id}/general-quota",
        headers={"Authorization": f"Bearer {school_bds_token}"},
    )
    assert response.status_code == 200, response.json()
    school_quota_json = response.json()
    assert school_quota_json["athlete_quota"] == 1, school_quota_json
    assert school_quota_json["cameraman_quota"] == 1, school_quota_json
    assert school_quota_json["pompom_quota"] == 1, school_quota_json
    assert school_quota_json["fanfare_quota"] == 1, school_quota_json


async def test_post_school_general_quota_as_random(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/schools/{school2.id}/general-quota",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "athlete_quota": 10,
            "cameraman_quota": 5,
            "pompom_quota": 3,
            "fanfare_quota": 2,
        },
    )
    assert response.status_code == 403, response.json()

    school_quota = client.get(
        f"/competition/schools/{school2.id}/general-quota",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert school_quota.status_code == 404, school_quota.json()


async def test_post_school_general_quota_as_admin(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/schools/{school2.id}/general-quota",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "athlete_quota": 10,
            "cameraman_quota": 5,
            "pompom_quota": 3,
            "fanfare_quota": 2,
        },
    )
    assert response.status_code == 201, response.json()

    school_quota = client.get(
        f"/competition/schools/{school2.id}/general-quota",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert school_quota.status_code == 200, school_quota.json()
    school_quota_json = school_quota.json()
    assert school_quota is not None, school_quota_json
    assert school_quota_json["athlete_quota"] == 10, school_quota_json
    assert school_quota_json["cameraman_quota"] == 5, school_quota_json
    assert school_quota_json["pompom_quota"] == 3, school_quota_json
    assert school_quota_json["fanfare_quota"] == 2, school_quota_json


async def test_patch_school_general_quota_as_random(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/schools/{school1.id}/general-quota",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "athlete_quota": 5,
            "cameraman_quota": 3,
            "pompom_quota": 2,
            "fanfare_quota": 1,
        },
    )
    assert response.status_code == 403, response.json()

    school_quota = client.get(
        f"/competition/schools/{school1.id}/general-quota",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert school_quota.status_code == 200, school_quota.json()
    school_quota_json = school_quota.json()
    assert school_quota_json["athlete_quota"] == 1, school_quota_json
    assert school_quota_json["cameraman_quota"] == 1, school_quota_json
    assert school_quota_json["pompom_quota"] == 1, school_quota_json
    assert school_quota_json["fanfare_quota"] == 1, school_quota_json


async def test_patch_school_general_quota_as_admin(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/schools/{school1.id}/general-quota",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "athlete_quota": 5,
            "cameraman_quota": 3,
            "pompom_quota": 2,
            "fanfare_quota": 1,
        },
    )
    assert response.status_code == 204, response.json()

    school_quota = client.get(
        f"/competition/schools/{school1.id}/general-quota",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert school_quota.status_code == 200, school_quota.json()
    school_quota_json = school_quota.json()
    assert school_quota_json["athlete_quota"] == 5, school_quota_json
    assert school_quota_json["cameraman_quota"] == 3, school_quota_json
    assert school_quota_json["pompom_quota"] == 2, school_quota_json
    assert school_quota_json["fanfare_quota"] == 1, school_quota_json


# endregion
# region: Sport Quotas


async def test_get_school_sport_quota(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/schools/{school1.id}/sports-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.json()
    quotas = response.json()
    assert len(quotas) > 0


async def test_get_sport_quota(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/sports/{sport_free_quota.id}/quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.json()
    quota = response.json()
    assert len(quota) > 0


async def test_post_school_sport_quota_as_random(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/schools/{school2.id}/sports/{sport_free_quota.id}/quotas",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "participant_quota": 5,
            "team_quota": 2,
        },
    )
    assert response.status_code == 403, response.json()

    quota = client.get(
        f"/competition/schools/{school2.id}/sports-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quota.status_code == 200, quota.json()
    quota_json = quota.json()
    sport_quota = next(
        (q for q in quota_json if q["sport_id"] == str(sport_free_quota.id)),
        None,
    )
    assert sport_quota is None, quota_json


async def test_post_school_sport_quota_as_admin(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/schools/{school2.id}/sports/{sport_free_quota.id}/quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "participant_quota": 5,
            "team_quota": 2,
        },
    )
    assert response.status_code == 204, response.text

    quota = client.get(
        f"/competition/schools/{school2.id}/sports-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quota.status_code == 200, quota.json()
    quota_json = quota.json()
    sport_quota = next(
        (q for q in quota_json if q["sport_id"] == str(sport_free_quota.id)),
        None,
    )
    assert sport_quota is not None, quota_json
    assert sport_quota["participant_quota"] == 5, quota_json
    assert sport_quota["team_quota"] == 2, quota_json


async def test_patch_school_sport_quota_as_random(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/schools/{school1.id}/sports/{sport_free_quota.id}/quotas",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "participant_quota": 3,
            "team_quota": 1,
        },
    )
    assert response.status_code == 403, response.json()

    quota = client.get(
        f"/competition/schools/{school1.id}/sports-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quota.status_code == 200, quota.json()
    quota_json = quota.json()
    sport_quota = next(
        (q for q in quota_json if q["sport_id"] == str(sport_free_quota.id)),
        None,
    )
    assert sport_quota is not None, quota_json
    assert sport_quota["participant_quota"] == 2, quota_json
    assert sport_quota["team_quota"] == 1, quota_json


async def test_patch_school_sport_quota_as_admin(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/schools/{school2.id}/sports/{sport_free_quota.id}/quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "participant_quota": 3,
            "team_quota": 1,
        },
    )
    assert response.status_code == 204, response.json()

    quota = client.get(
        f"/competition/schools/{school2.id}/sports-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quota.status_code == 200, quota.json()
    quota_json = quota.json()
    sport_quota = next(
        (q for q in quota_json if q["sport_id"] == str(sport_free_quota.id)),
        None,
    )
    assert sport_quota is not None, quota_json
    assert sport_quota["participant_quota"] == 3, quota_json
    assert sport_quota["team_quota"] == 1, quota_json


async def test_delete_school_sport_quota_as_random(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/schools/{school1.id}/sports/{sport_free_quota.id}/quotas",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()

    quota = client.get(
        f"/competition/schools/{school1.id}/sports-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quota.status_code == 200, quota.json()
    quota_json = quota.json()
    sport_quota = next(
        (q for q in quota_json if q["sport_id"] == str(sport_free_quota.id)),
        None,
    )
    assert sport_quota is not None, quota_json


async def test_delete_school_sport_quota_as_admin(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/schools/{school2.id}/sports/{sport_free_quota.id}/quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204, response.json()

    quota = client.get(
        f"/competition/schools/{school2.id}/sports-quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quota.status_code == 200, quota.json()
    quota_json = quota.json()
    sport_quota = next(
        (q for q in quota_json if q["sport_id"] == str(sport_free_quota.id)),
        None,
    )
    assert sport_quota is None, quota_json


# endregion
# region: Teams


async def test_get_user_team_as_captain(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/teams/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.json()
    team = response.json()
    assert team["id"] == str(team_admin_user.id)


async def test_get_sport_teams(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/teams/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    teams = response.json()
    assert len(teams) == 2


async def test_get_school_teams(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/teams/schools/{school1.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    teams = response.json()
    assert len(teams) == 1


async def test_get_sport_team_for_school(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/teams/sports/{sport_with_team.id}/schools/{school1.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    teams = response.json()
    assert len(teams) == 1


async def test_create_team_different_captain(
    client: TestClient,
) -> None:
    team_info = TeamInfo(
        name="New Team",
        school_id=school1.id,
        sport_id=sport_with_team.id,
        captain_id=school_bds_user.id,
    )
    response = client.post(
        "/competition/teams",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=team_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 403, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_free_quota.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    new_team_check = next(
        (t for t in teams_json if t["captain_id"] == str(school_bds_user.id)),
        None,
    )
    assert new_team_check is None, teams_json


async def test_create_team_different_school(
    client: TestClient,
) -> None:
    team_info = TeamInfo(
        name="New Team",
        school_id=school2.id,
        sport_id=sport_with_team.id,
        captain_id=user3.id,
    )
    response = client.post(
        "/competition/teams",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=team_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 403, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_free_quota.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    new_team_check = next(
        (t for t in teams_json if t["school_id"] == str(school2.id)),
        None,
    )
    assert new_team_check is None, teams_json


async def test_create_team_for_sport_without_team(
    client: TestClient,
) -> None:
    team_info = TeamInfo(
        name="New Team",
        school_id=SchoolType.centrale_lyon.value,
        sport_id=sport_free_quota.id,
        captain_id=user3.id,
    )
    response = client.post(
        "/competition/teams",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=team_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 400, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_free_quota.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    new_team_check = next((t for t in teams_json if t["name"] == "New Team"), None)
    assert new_team_check is None, teams_json


async def test_create_team_no_quota(
    client: TestClient,
) -> None:
    strict_quota = models_sport_competition.SchoolSportQuota(
        school_id=school1.id,
        edition_id=active_edition.id,
        sport_id=sport_with_team.id,
        participant_quota=0,
        team_quota=0,
    )
    await add_object_to_db(strict_quota)

    team_info = TeamInfo(
        name="New Team",
        school_id=school1.id,
        sport_id=sport_with_team.id,
        captain_id=school_bds_user.id,
    )
    response = client.post(
        "/competition/teams",
        headers={"Authorization": f"Bearer {school_bds_token}"},
        json=team_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 400, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    new_team_check = next((t for t in teams_json if t["name"] == "New Team"), None)
    assert new_team_check is None, teams_json


async def test_create_team_used_name(
    client: TestClient,
) -> None:
    team_info = TeamInfo(
        name=team1.name,
        school_id=SchoolType.centrale_lyon.value,
        sport_id=sport_with_team.id,
        captain_id=user3.id,
    )
    response = client.post(
        "/competition/teams",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=team_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 400, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    new_team_check = next((t for t in teams_json if t["name"] == team1.name), None)
    assert new_team_check is not None, teams_json


async def test_create_team(
    client: TestClient,
) -> None:
    team_info = TeamInfo(
        name="New Team",
        school_id=SchoolType.centrale_lyon.value,
        sport_id=sport_with_team.id,
        captain_id=user3.id,
    )
    response = client.post(
        "/competition/teams",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=team_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 201, response.json()
    team = response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    new_team_check = next((t for t in teams_json if t["id"] == team["id"]), None)
    assert new_team_check is not None, teams_json


async def test_patch_team_as_random(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/teams/{team1.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "name": "Unauthorized Team Update",
        },
    )
    assert response.status_code == 403, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    updated_team_check = next((t for t in teams_json if t["id"] == str(team1.id)), None)
    assert updated_team_check is not None
    assert updated_team_check["name"] == team1.name


async def test_patch_team_as_admin(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/teams/{team1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Updated Team Name",
        },
    )
    assert response.status_code == 204, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    updated_team_check = next((t for t in teams_json if t["id"] == str(team1.id)), None)
    assert updated_team_check is not None
    assert updated_team_check["name"] == "Updated Team Name"


async def test_patch_team_as_captain(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/teams/{team1.id}",
        headers={"Authorization": f"Bearer {sport_manager_token}"},
        json={
            "name": "Captain Updated Team Name",
        },
    )
    assert response.status_code == 204, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    updated_team_check = next((t for t in teams_json if t["id"] == str(team1.id)), None)
    assert updated_team_check is not None
    assert updated_team_check["name"] == "Captain Updated Team Name"


async def test_delete_team_as_random(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/teams/{team1.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    deleted_team_check = next((t for t in teams_json if t["id"] == str(team1.id)), None)
    assert deleted_team_check is not None, teams_json


async def test_delete_team_as_admin(
    client: TestClient,
) -> None:
    new_team = models_sport_competition.CompetitionTeam(
        id=uuid4(),
        name="Team to Delete",
        school_id=SchoolType.centrale_lyon.value,
        edition_id=active_edition.id,
        sport_id=sport_with_team.id,
        captain_id=user3.id,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(new_team)
    response = client.delete(
        f"/competition/teams/{new_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    deleted_team_check = next(
        (t for t in teams_json if t["id"] == str(new_team.id)),
        None,
    )
    assert deleted_team_check is None, teams_json


async def test_delete_team_as_captain(
    client: TestClient,
) -> None:
    new_team = models_sport_competition.CompetitionTeam(
        id=uuid4(),
        name="Team to Delete",
        school_id=SchoolType.centrale_lyon.value,
        edition_id=active_edition.id,
        sport_id=sport_with_team.id,
        captain_id=user3.id,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(new_team)
    response = client.delete(
        f"/competition/teams/{new_team.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 204, response.json()

    teams = client.get(
        f"/competition/teams/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert teams.status_code == 200, teams.json()
    teams_json = teams.json()
    deleted_team_check = next(
        (t for t in teams_json if t["id"] == str(new_team.id)),
        None,
    )
    assert deleted_team_check is None, teams_json


# endregion
# region: Participants


async def test_get_participant_me(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/participants/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.json()
    user = response.json()
    assert user["user_id"] == str(admin_user.id)
    assert user["sport_id"] == str(sport_free_quota.id)
    assert user["edition_id"] == str(active_edition.id)


async def test_get_participant_for_sport(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/participants/sports/{sport_free_quota.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.json()
    users = response.json()
    assert len(users) > 0
    assert all(user["edition_id"] == str(active_edition.id) for user in users)
    assert all(user["sport_id"] == str(sport_free_quota.id) for user in users)


async def test_get_participant_for_school_as_admin(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/participants/schools/{SchoolType.centrale_lyon.value}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.json()
    users = response.json()
    assert len(users) > 0
    assert all(user["edition_id"] == str(active_edition.id) for user in users)
    assert all(
        user["school_id"] == str(SchoolType.centrale_lyon.value) for user in users
    )


async def test_get_participant_for_school_as_school_student(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/participants/schools/{SchoolType.centrale_lyon.value}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    users = response.json()
    assert len(users) > 0
    assert all(user["edition_id"] == str(active_edition.id) for user in users)
    assert all(
        user["school_id"] == str(SchoolType.centrale_lyon.value) for user in users
    )


async def test_get_participant_for_school_as_random(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/participants/schools/{school1.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()
    assert "Unauthorized action" in response.json()["detail"]


async def test_user_participate_with_invalid_category(
    client: TestClient,
) -> None:
    info = ParticipantInfo(
        license="12345670089",
        substitute=False,
    )
    response = client.post(
        f"/competition/sports/{sport_feminine.id}/participate",
        headers={"Authorization": f"Bearer {school_bds_token}"},
        json=info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 403, response.json()
    assert (
        "Sport category does not match user sport category" in response.json()["detail"]
    )

    participants = client.get(
        f"/competition/participants/sports/{sport_feminine.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    assert not any(
        p["user_id"] == str(school_bds_user.id) for p in participants_json
    ), participants_json


async def test_user_participate_without_team(
    client: TestClient,
) -> None:
    info = ParticipantInfo(
        license="12345670089",
        substitute=False,
    )
    response = client.post(
        f"/competition/sports/{sport_with_team.id}/participate",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 400, response.json()
    assert "Sport declared needs to be played in a team" in response.json()["detail"]

    participants = client.get(
        f"/competition/participants/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    assert not any(p["user_id"] == str(user3.id) for p in participants_json), (
        participants_json
    )


async def test_user_participate_with_invalid_team_school(
    client: TestClient,
) -> None:
    info = ParticipantInfo(
        license="12345670089",
        substitute=False,
        team_id=team2.id,  # team2 is from a different school
    )
    response = client.post(
        f"/competition/sports/{sport_with_team.id}/participate",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 403, response.json()
    assert (
        "Unauthorized action, team does not belong to user school"
        in response.json()["detail"]
    )

    participants = client.get(
        f"/competition/participants/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    assert not any(p["user_id"] == str(user3.id) for p in participants_json), (
        participants_json
    )


async def test_user_participate_with_unknown_team(
    client: TestClient,
) -> None:
    info = ParticipantInfo(
        license="12345670089",
        substitute=False,
        team_id=uuid4(),
    )
    response = client.post(
        f"/competition/sports/{sport_with_team.id}/participate",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 404, response.json()
    assert "Team not found in the database" in response.json()["detail"]

    participants = client.get(
        f"/competition/participants/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    assert not any(p["user_id"] == str(user3.id) for p in participants_json), (
        participants_json
    )


async def test_user_participate_with_maximum_team_size(
    client: TestClient,
) -> None:
    new_user, _, new_user_token = await create_competition_user(
        edition_id=active_edition.id,
        school_id=SchoolType.centrale_lyon.value,
        sport_category=SportCategory.masculine,
    )
    async with get_TestingSessionLocal()() as db:
        await db.execute(
            update(models_sport_competition.Sport)
            .where(
                models_sport_competition.Sport.id == sport_with_team.id,
            )
            .values(
                team_size=2,  # Set team size to 1 for testing
            ),
        )
        await db.commit()

    info = ParticipantInfo(
        license="12345670089",
        substitute=False,
        team_id=team1.id,  # team1 is from the same school
    )
    response = client.post(
        f"/competition/sports/{sport_with_team.id}/participate",
        headers={"Authorization": f"Bearer {new_user_token}"},
        json=info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 400, response.json()
    assert "Maximum number of players in the team reached" in response.json()["detail"]

    async with get_TestingSessionLocal()() as db:
        await db.execute(
            update(models_sport_competition.Sport)
            .where(
                models_sport_competition.Sport.id == sport_with_team.id,
            )
            .values(
                team_size=5,  # Reset team size to a valid number
            ),
        )
        await db.commit()

    participants = client.get(
        f"/competition/participants/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    assert not any(p["user_id"] == str(new_user.id) for p in participants_json), (
        participants_json
    )


async def test_user_participate_with_maximum_substitute_size(
    client: TestClient,
) -> None:
    info = ParticipantInfo(
        license="12345670089",
        substitute=True,
        team_id=team1.id,  # team1 is from the same school
    )
    response = client.post(
        f"/competition/sports/{sport_with_team.id}/participate",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 400, response.json()
    assert (
        "Maximum number of substitutes in the team reached" in response.json()["detail"]
    )

    participants = client.get(
        f"/competition/participants/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    assert not any(p["user_id"] == str(user3.id) for p in participants_json), (
        participants_json
    )


async def test_user_participate_with_valid_data(
    client: TestClient,
) -> None:
    info = ParticipantInfo(
        license="12345670089",
        substitute=False,
    )
    response = client.post(
        f"/competition/sports/{sport_free_quota.id}/participate",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 201, response.json()

    participants = client.get(
        f"/competition/participants/sports/{sport_free_quota.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    user_participation = next(
        (u for u in participants_json if u["user_id"] == str(user3.id)),
        None,
    )
    assert user_participation is not None, participants_json
    assert user_participation["edition_id"] == str(active_edition.id)


async def test_user_participate_with_team(
    client: TestClient,
) -> None:
    async with get_TestingSessionLocal()() as db:
        await db.execute(
            delete(models_sport_competition.CompetitionParticipant).where(
                models_sport_competition.CompetitionParticipant.user_id == user3.id,
            ),
        )
        await db.commit()
    info = ParticipantInfo(
        license="12345670089",
        substitute=False,
        team_id=team1.id,  # team1 is from the same school
    )
    response = client.post(
        f"/competition/sports/{sport_with_team.id}/participate",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 201, response.json()

    participants = client.get(
        f"/competition/participants/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    user_participation = next(
        (u for u in participants_json if u["user_id"] == str(user3.id)),
        None,
    )
    assert user_participation is not None, participants_json
    assert user_participation["edition_id"] == str(active_edition.id)


async def test_add_user_certificate(
    client: TestClient,
):
    file = b"this is a test file"
    file_content = {
        "certificate": ("test_certificate.pdf", file, "application/pdf"),
    }
    response = client.post(
        f"/competition/participants/sports/{sport_free_quota.id}/certificate",
        headers={"Authorization": f"Bearer {admin_token}"},
        files=file_content,
    )
    assert response.status_code == 204, response.json()

    participants = client.get(
        f"/competition/participants/sports/{sport_free_quota.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    user_participation = next(
        (u for u in participants_json if u["user_id"] == str(admin_user.id)),
        None,
    )
    assert user_participation is not None, participants_json
    assert user_participation["certificate_file_id"] is not None, participants_json

    file_response = client.get(
        f"/competition/participants/users/{admin_user.id}/certificate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert file_response.status_code == 200, file_response.json()
    assert file_response.content == file, file_response.json()


async def test_delete_user_certificate(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/participants/sports/{sport_free_quota.id}/certificate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204, response.json()

    participants = client.get(
        f"/competition/participants/sports/{sport_free_quota.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    user_participation = next(
        (u for u in participants_json if u["user_id"] == str(admin_user.id)),
        None,
    )
    assert user_participation is not None, participants_json
    assert user_participation["certificate_file_id"] is None, participants_json


async def test_user_withdraw_participation(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/sports/{sport_with_team.id}/withdraw",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 204, response.json()

    participants = client.get(
        f"/competition/participants/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert participants.status_code == 200, participants.json()
    participants_json = participants.json()
    user_participation = next(
        (u for u in participants_json if u["user_id"] == str(user3.id)),
        None,
    )
    assert user_participation is None, participants_json


# endregion
# region: Locations


async def test_get_locations(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/locations",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    locations = response.json()
    assert len(locations) == 1
    assert locations[0]["name"] == "Main Stadium"


async def test_get_location_by_id(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/locations/{location.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    location_json = response.json()
    assert location_json["name"] == "Main Stadium"
    assert len(location_json["matches"]) == 1


async def test_post_location_as_random(
    client: TestClient,
) -> None:
    location_info = LocationBase(
        name="New Location",
        description="A new location for testing",
        address="123 Main St",
        latitude=45.0,
        longitude=4.0,
    )
    response = client.post(
        "/competition/locations",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=location_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 403, response.json()

    locations = client.get(
        "/competition/locations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert locations.status_code == 200, locations.json()
    locations_json = locations.json()
    new_location_check = next(
        (location for location in locations_json if location["name"] == "New Location"),
        None,
    )
    assert new_location_check is None, locations_json


async def test_post_location_as_admin(
    client: TestClient,
) -> None:
    location_info = LocationBase(
        name="New Location",
        description="A new location for testing",
        address="123 Main St",
        latitude=45.0,
        longitude=4.0,
    )
    response = client.post(
        "/competition/locations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=location_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 201, response.json()
    location = response.json()

    locations = client.get(
        "/competition/locations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert locations.status_code == 200, locations.json()
    locations_json = locations.json()
    new_location_check = next(
        (loc for loc in locations_json if loc["id"] == location["id"]),
        None,
    )
    assert new_location_check is not None, locations_json


async def test_patch_location_as_random(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/locations/{location.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "name": "Unauthorized Location Update",
        },
    )
    assert response.status_code == 403, response.json()

    locations = client.get(
        "/competition/locations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert locations.status_code == 200, locations.json()
    locations_json = locations.json()
    updated_location_check = next(
        (loc for loc in locations_json if loc["id"] == str(location.id)),
        None,
    )
    assert updated_location_check is not None
    assert updated_location_check["name"] == location.name


async def test_patch_location_as_admin(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/locations/{location.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Updated Location Name",
        },
    )
    assert response.status_code == 204, response.json()

    locations = client.get(
        "/competition/locations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert locations.status_code == 200, locations.json()
    locations_json = locations.json()
    updated_location_check = next(
        (loc for loc in locations_json if loc["id"] == str(location.id)),
        None,
    )
    assert updated_location_check is not None
    assert updated_location_check["name"] == "Updated Location Name"


async def delete_location_as_random(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/locations/{location.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()

    locations = client.get(
        "/competition/locations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert locations.status_code == 200, locations.json()
    locations_json = locations.json()
    deleted_location_check = next(
        (loc for loc in locations_json if loc["id"] == str(location.id)),
        None,
    )
    assert deleted_location_check is not None, locations_json


async def test_delete_location_as_admin(
    client: TestClient,
) -> None:
    new_location = models_sport_competition.MatchLocation(
        id=uuid4(),
        name="Location to Delete",
        description="A location to delete",
        address="456 Secondary St",
        edition_id=active_edition.id,
        latitude=46.0,
        longitude=5.0,
    )
    await add_object_to_db(new_location)
    response = client.delete(
        f"/competition/locations/{new_location.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204, response.json()

    locations = client.get(
        "/competition/locations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert locations.status_code == 200, locations.json()
    locations_json = locations.json()
    deleted_location_check = next(
        (loc for loc in locations_json if loc["id"] == str(new_location.id)),
        None,
    )
    assert deleted_location_check is None, locations_json


# endregion
# region: Matches


async def test_gest_sport_matches(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    matches = response.json()
    assert len(matches) == 1
    assert matches[0]["name"] == "Match 1"


async def test_gest_school_matches(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/matches/schools/{school1.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    matches = response.json()
    assert len(matches) == 1
    assert matches[0]["name"] == "Match 1"


async def test_create_match_as_random(
    client: TestClient,
) -> None:
    match_info = MatchBase(
        name="New Match",
        team1_id=team1.id,
        team2_id=team2.id,
        description="A new match for testing",
        sport_id=sport_with_team.id,
        location_id=location.id,
        date=datetime.now(UTC),
    )
    response = client.post(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=match_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 403, response.json()

    matches = client.get(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert matches.status_code == 200, matches.json()
    matches_json = matches.json()
    new_match_check = next(
        (match for match in matches_json if match["name"] == "New Match"),
        None,
    )
    assert new_match_check is None, matches_json


async def test_create_match_as_admin(
    client: TestClient,
) -> None:
    match_info = MatchBase(
        name="New Match",
        team1_id=team1.id,
        team2_id=team2.id,
        description="A new match for testing",
        sport_id=sport_with_team.id,
        location_id=location.id,
        date=datetime(2024, 6, 15, 15, 0, 0, tzinfo=UTC),
    )
    response = client.post(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=match_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 201, response.json()
    match = response.json()

    matches = client.get(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert matches.status_code == 200, matches.json()
    matches_json = matches.json()
    new_match_check = next(
        (m for m in matches_json if m["id"] == match["id"]),
        None,
    )
    assert new_match_check is not None, matches_json


async def test_patch_match_as_random(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/matches/{match1.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "name": "Unauthorized Match Update",
        },
    )
    assert response.status_code == 403, response.json()

    matches = client.get(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert matches.status_code == 200, matches.json()
    matches_json = matches.json()
    updated_match_check = next(
        (m for m in matches_json if m["id"] == str(match1.id)),
        None,
    )
    assert updated_match_check is not None
    assert updated_match_check["name"] == match1.name


async def test_patch_match_as_admin(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/matches/{match1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Updated Match Name",
            "score_team1": 3,
            "score_team2": 2,
            "winner_id": str(team1.id),
        },
    )
    assert response.status_code == 204, response.json()

    matches = client.get(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert matches.status_code == 200, matches.json()
    matches_json = matches.json()
    updated_match_check = next(
        (m for m in matches_json if m["id"] == str(match1.id)),
        None,
    )
    assert updated_match_check is not None
    assert updated_match_check["name"] == "Updated Match Name"
    assert updated_match_check["score_team1"] == 3
    assert updated_match_check["score_team2"] == 2
    assert updated_match_check["winner_id"] == str(team1.id)


async def test_edit_match_as_sport_manager(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/matches/{match1.id}",
        headers={"Authorization": f"Bearer {user4_token}"},
        json={
            "name": "Sport Manager Updated Match Name",
            "score_team1": 1,
            "score_team2": 1,
            "winner_id": None,
        },
    )
    assert response.status_code == 204, response.json()

    matches = client.get(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert matches.status_code == 200, matches.json()
    matches_json = matches.json()
    updated_match_check = next(
        (m for m in matches_json if m["id"] == str(match1.id)),
        None,
    )
    assert updated_match_check is not None
    assert updated_match_check["name"] == "Sport Manager Updated Match Name"
    assert updated_match_check["score_team1"] == 1
    assert updated_match_check["score_team2"] == 1
    assert updated_match_check["winner_id"] is None


async def test_delete_match_as_random(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/matches/{match1.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.text

    matches = client.get(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert matches.status_code == 200, matches.json()
    matches_json = matches.json()
    deleted_match_check = next(
        (m for m in matches_json if m["id"] == str(match1.id)),
        None,
    )
    assert deleted_match_check is not None, matches_json


async def test_delete_match_as_admin(
    client: TestClient,
) -> None:
    new_match = models_sport_competition.Match(
        id=uuid4(),
        name="Match to Delete",
        team1_id=team1.id,
        team2_id=team2.id,
        sport_id=sport_with_team.id,
        location_id=location.id,
        edition_id=active_edition.id,
        date=datetime.now(UTC),
        score_team1=None,
        score_team2=None,
        winner_id=None,
    )
    await add_object_to_db(new_match)
    response = client.delete(
        f"/competition/matches/{new_match.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204, response.text

    matches = client.get(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert matches.status_code == 200, matches.json()
    matches_json = matches.json()
    deleted_match_check = next(
        (m for m in matches_json if m["id"] == str(new_match.id)),
        None,
    )
    assert deleted_match_check is None, matches_json


async def test_delete_match_as_sport_manager(
    client: TestClient,
) -> None:
    new_match = models_sport_competition.Match(
        id=uuid4(),
        name="Match to Delete",
        team1_id=team1.id,
        team2_id=team2.id,
        sport_id=sport_with_team.id,
        location_id=location.id,
        edition_id=active_edition.id,
        date=datetime.now(UTC),
        score_team1=None,
        score_team2=None,
        winner_id=None,
    )
    await add_object_to_db(new_match)
    response = client.delete(
        f"/competition/matches/{new_match.id}",
        headers={"Authorization": f"Bearer {user4_token}"},
    )
    assert response.status_code == 204, response.text

    matches = client.get(
        f"/competition/matches/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert matches.status_code == 200, matches.json()
    matches_json = matches.json()
    deleted_match_check = next(
        (m for m in matches_json if m["id"] == str(new_match.id)),
        None,
    )
    assert deleted_match_check is None, matches_json


# endregion
# region: Podiums
async def test_get_global_podiums(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/podiums/global",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    podiums = response.json()
    assert len(podiums) == 2
    centrale_score = next(
        (p for p in podiums if p["school_id"] == str(SchoolType.centrale_lyon.value)),
        None,
    )
    assert centrale_score is not None
    assert centrale_score["total_points"] == 30
    other_school_score = next(
        (p for p in podiums if p["school_id"] == str(school1.id)),
        None,
    )
    assert other_school_score is not None
    assert other_school_score["total_points"] == 4


async def test_get_sport_podiums(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/podiums/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 200, response.json()
    podiums = response.json()
    assert len(podiums) == 3


async def test_post_podium_as_random(
    client: TestClient,
) -> None:
    podium_info = SportPodiumRankings(
        rankings=[
            TeamSportResultBase(
                sport_id=sport_with_team.id,
                school_id=SchoolType.centrale_lyon.value,
                points=15,
                team_id=team1.id,
            ),
        ],
    )

    response = client.post(
        f"/competition/podiums/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=podium_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 403, response.json()

    podiums = client.get(
        f"/competition/podiums/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert podiums.status_code == 200, podiums.json()
    podiums_json = podiums.json()
    podium_check = next(
        (p for p in podiums_json if p["points"] == 15),
        None,
    )
    assert podium_check is None, podiums_json


async def test_post_podium_as_sport_manager(
    client: TestClient,
) -> None:
    podium_info = SportPodiumRankings(
        rankings=[
            TeamSportResultBase(
                sport_id=sport_with_team.id,
                school_id=SchoolType.centrale_lyon.value,
                points=15,
                team_id=team1.id,
            ),
            TeamSportResultBase(
                sport_id=sport_with_team.id,
                school_id=school1.id,
                points=10,
                team_id=team2.id,
            ),
            TeamSportResultBase(
                sport_id=sport_with_team.id,
                school_id=SchoolType.centrale_lyon.value,
                points=5,
                team_id=team_admin_user.id,
            ),
        ],
    )

    response = client.post(
        f"/competition/podiums/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {user4_token}"},
        json=podium_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 201, response.json()

    podiums = client.get(
        f"/competition/podiums/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert podiums.status_code == 200, podiums.json()
    podiums_json = podiums.json()
    podium_check = next(
        (p for p in podiums_json if p["points"] == 15),
        None,
    )
    assert podium_check is not None, podiums_json
    podium_check = next(
        (p for p in podiums_json if p["points"] == 10),
        None,
    )
    assert podium_check is not None, podiums_json
    podium_check = next(
        (p for p in podiums_json if p["points"] == 5),
        None,
    )
    assert podium_check is not None, podiums_json


async def test_delete_podium_as_random(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/podiums/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()

    podiums = client.get(
        f"/competition/podiums/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert podiums.status_code == 200, podiums.json()
    podiums_json = podiums.json()
    assert len(podiums_json) == 3, podiums_json


async def test_delete_podium_as_sport_manager(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/podiums/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {user4_token}"},
    )
    assert response.status_code == 204, response.json()

    podiums = client.get(
        f"/competition/podiums/sports/{sport_with_team.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert podiums.status_code == 200, podiums.json()
    podiums_json = podiums.json()
    assert len(podiums_json) == 0, podiums_json


# endregion
# region: Volunteers Shifts


async def test_get_volunteer_shifts(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/volunteers/shifts",
        headers={"Authorization": f"Bearer {user3_token}"},
    )

    assert response.status_code == 200, response.json()
    shifts = response.json()
    assert len(shifts) == 1
    assert shifts[0]["name"] == "Morning Shift"


async def test_create_volunteer_shift_as_random(
    client: TestClient,
) -> None:
    shift_info = VolunteerShiftBase(
        name="New Shift",
        description="A new shift for testing",
        value=1,
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(hours=2),
        location="Event Hall",
        max_volunteers=5,
    )
    response = client.post(
        "/competition/volunteers/shifts",
        headers={"Authorization": f"Bearer {user3_token}"},
        json=shift_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 403, response.json()

    shifts = client.get(
        "/competition/volunteers/shifts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert shifts.status_code == 200, shifts.json()
    shifts_json = shifts.json()
    new_shift_check = next(
        (shift for shift in shifts_json if shift["name"] == "New Shift"),
        None,
    )
    assert new_shift_check is None, shifts_json


async def test_create_volunteer_shift_as_admin(
    client: TestClient,
) -> None:
    shift_info = VolunteerShiftBase(
        name="New Shift",
        description="A new shift for testing",
        value=1,
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(hours=2),
        location="Event Hall",
        max_volunteers=5,
    )
    response = client.post(
        "/competition/volunteers/shifts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=shift_info.model_dump(exclude_none=True, mode="json"),
    )
    assert response.status_code == 201, response.json()
    shift = response.json()

    shifts = client.get(
        "/competition/volunteers/shifts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert shifts.status_code == 200, shifts.json()
    shifts_json = shifts.json()
    new_shift_check = next(
        (s for s in shifts_json if s["id"] == shift["id"]),
        None,
    )
    assert new_shift_check is not None, shifts_json


async def test_patch_volunteer_shift_as_random(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/volunteers/shifts/{volunteer_shift.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
        json={
            "name": "Unauthorized Shift Update",
        },
    )
    assert response.status_code == 403, response.json()

    shifts = client.get(
        "/competition/volunteers/shifts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert shifts.status_code == 200, shifts.json()
    shifts_json = shifts.json()
    updated_shift_check = next(
        (s for s in shifts_json if s["id"] == str(volunteer_shift.id)),
        None,
    )
    assert updated_shift_check is not None
    assert updated_shift_check["name"] == volunteer_shift.name


async def test_patch_volunteer_shift_as_admin(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/volunteers/shifts/{volunteer_shift.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Updated Shift Name",
        },
    )
    assert response.status_code == 204, response.json()

    shifts = client.get(
        "/competition/volunteers/shifts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert shifts.status_code == 200, shifts.json()
    shifts_json = shifts.json()
    updated_shift_check = next(
        (s for s in shifts_json if s["id"] == str(volunteer_shift.id)),
        None,
    )
    assert updated_shift_check is not None
    assert updated_shift_check["name"] == "Updated Shift Name"


async def test_delete_volunteer_shift_as_random(
    client: TestClient,
) -> None:
    response = client.delete(
        f"/competition/volunteers/shifts/{volunteer_shift.id}",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()

    shifts = client.get(
        "/competition/volunteers/shifts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert shifts.status_code == 200, shifts.json()
    shifts_json = shifts.json()
    deleted_shift_check = next(
        (s for s in shifts_json if s["id"] == str(volunteer_shift.id)),
        None,
    )
    assert deleted_shift_check is not None, shifts_json


async def test_delete_volunteer_shift_as_admin(
    client: TestClient,
) -> None:
    new_shift = models_sport_competition.VolunteerShift(
        id=uuid4(),
        name="Shift to Delete",
        description="A shift to delete",
        value=1,
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(hours=2),
        location="Event Hall",
        max_volunteers=5,
        edition_id=active_edition.id,
    )
    await add_object_to_db(new_shift)
    new_registration = models_sport_competition.VolunteerRegistration(
        shift_id=new_shift.id,
        user_id=user3.id,
        edition_id=active_edition.id,
        registered_at=datetime.now(UTC),
        validated=True,
    )
    await add_object_to_db(new_registration)
    response = client.delete(
        f"/competition/volunteers/shifts/{new_shift.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204, response.json()

    shifts = client.get(
        "/competition/volunteers/shifts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert shifts.status_code == 200, shifts.json()
    shifts_json = shifts.json()
    deleted_shift_check = next(
        (s for s in shifts_json if s["id"] == str(new_shift.id)),
        None,
    )
    assert deleted_shift_check is None, shifts_json

    registrations = client.get(
        "/competition/volunteers/me",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert registrations.status_code == 200, registrations.json()
    registrations_json = registrations.json()
    deleted_registration_check = next(
        (r for r in registrations_json if r["shift_id"] == str(new_shift.id)),
        None,
    )
    assert deleted_registration_check is None, registrations_json


# endregion
# region: Volunteer Registrations


async def test_get_own_volunteer_registrations(
    client: TestClient,
) -> None:
    response = client.get(
        "/competition/volunteers/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.json()
    registrations = response.json()
    assert len(registrations) == 1
    assert registrations[0]["shift_id"] == str(volunteer_shift.id)


async def test_register_to_shift_as_non_volunteer(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/volunteers/shifts/{volunteer_shift.id}/register",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 403, response.json()
    assert (
        "You must be registered for the competition as a volunteer to register for a volunteer shift"
        in response.json()["detail"]
    )

    registrations = client.get(
        "/competition/volunteers/me",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert registrations.status_code == 200, registrations.json()
    registrations_json = registrations.json()
    registration_check = next(
        (r for r in registrations_json if r["shift_id"] == str(volunteer_shift.id)),
        None,
    )
    assert registration_check is None, registrations_json


async def test_register_already_registered_to_shift(
    client: TestClient,
) -> None:
    response = client.post(
        f"/competition/volunteers/shifts/{volunteer_shift.id}/register",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400, response.json()
    assert (
        "You are already registered to this volunteer shift."
        in response.json()["detail"]
    )


async def test_register_to_full_shift(
    client: TestClient,
) -> None:
    async with get_TestingSessionLocal()() as db:
        await db.execute(
            update(models_sport_competition.CompetitionUser)
            .where(models_sport_competition.CompetitionUser.user_id == user3.id)
            .values(is_volunteer=True),
        )
        await db.commit()

    response = client.post(
        f"/competition/volunteers/shifts/{volunteer_shift.id}/register",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert response.status_code == 400
    assert "This volunteer shift is full." in response.json()["detail"]

    registrations = client.get(
        "/competition/volunteers/me",
        headers={"Authorization": f"Bearer {user3_token}"},
    )
    assert registrations.status_code == 200, registrations.json()
    registrations_json = registrations.json()
    registration_check = next(
        (r for r in registrations_json if r["shift_id"] == str(volunteer_shift.id)),
        None,
    )
    assert registration_check is None, registrations_json


async def test_register_to_volunteer_shift(
    client: TestClient,
) -> None:
    new_shift = models_sport_competition.VolunteerShift(
        id=uuid4(),
        name="Another Shift",
        description="Another shift for testing",
        value=1,
        start_time=datetime.now(UTC) + timedelta(days=1),
        end_time=datetime.now(UTC) + timedelta(days=1, hours=2),
        location="Event Hall",
        max_volunteers=5,
        edition_id=active_edition.id,
    )
    await add_object_to_db(new_shift)

    response = client.post(
        f"/competition/volunteers/shifts/{new_shift.id}/register",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204, response.json()

    registrations = client.get(
        "/competition/volunteers/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert registrations.status_code == 200, registrations.json()
    registrations_json = registrations.json()
    registration_check = next(
        (r for r in registrations_json if r["shift_id"] == str(volunteer_shift.id)),
        None,
    )
    assert registration_check is not None, registrations_json


async def test_data_exporter(
    client: TestClient,
):
    response = client.get(
        "/competition/users/data-export?included_fields=purchases&included_fields=payments&included_fields=participants",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
