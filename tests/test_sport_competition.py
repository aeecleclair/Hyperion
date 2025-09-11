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

school1: models_schools.CoreSchool
school2: models_schools.CoreSchool

active_edition: models_sport_competition.CompetitionEdition
old_edition: models_sport_competition.CompetitionEdition

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
school1_extension: models_sport_competition.SchoolExtension
ecl_general_quota: models_sport_competition.SchoolGeneralQuota
school_general_quota: models_sport_competition.SchoolGeneralQuota

sport_free_quota: models_sport_competition.Sport
sport_used_quota: models_sport_competition.Sport
sport_with_team: models_sport_competition.Sport
sport_with_substitute: models_sport_competition.Sport
ecl_sport_free_quota: models_sport_competition.SchoolSportQuota
ecl_sport_used_quota: models_sport_competition.SchoolSportQuota

team1: models_sport_competition.CompetitionTeam
team2: models_sport_competition.CompetitionTeam

participant1: models_sport_competition.CompetitionParticipant
participant2: models_sport_competition.CompetitionParticipant


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global school1, school2, active_edition, old_edition
    school1 = models_schools.CoreSchool(
        id=uuid.uuid4(),
        name="Emlyon Business School",
        email_regex=r"^[a-zA-Z0-9._%+-]+@edu.emlyon.fr$",
    )
    await add_object_to_db(school1)
    school2 = models_schools.CoreSchool(
        id=uuid.uuid4(),
        name="Centrale Supelec",
        email_regex=r"^[a-zA-Z0-9._%+-]+@edu.centralesupelec.fr$",
    )
    await add_object_to_db(school2)
    old_edition = models_sport_competition.CompetitionEdition(
        id=uuid.uuid4(),
        name="Edition 2023",
        year=2023,
        start_date=datetime(2023, 1, 1, tzinfo=UTC),
        end_date=datetime(2023, 12, 31, tzinfo=UTC),
        active=False,
        inscription_enabled=False,
    )
    await add_object_to_db(old_edition)
    active_edition = models_sport_competition.CompetitionEdition(
        id=uuid.uuid4(),
        name="Edition 2024",
        year=2024,
        start_date=datetime(2024, 1, 1, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, tzinfo=UTC),
        active=True,
        inscription_enabled=True,
    )
    await add_object_to_db(active_edition)

    global admin_user, school_bds_user, sport_manager_user, user3
    admin_user = await create_user_with_groups(
        [GroupType.competition_admin],
    )
    school_bds_user = await create_user_with_groups(
        [],
        school_id=school1.id,
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
        edition_id=active_edition.id,
        is_athlete=True,
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
        active=True,
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
    )
    await add_object_to_db(ecl_general_quota)
    school_general_quota = models_sport_competition.SchoolGeneralQuota(
        school_id=school1.id,
        edition_id=active_edition.id,
        athlete_quota=1,
        cameraman_quota=1,
        pompom_quota=1,
        fanfare_quota=1,
    )
    await add_object_to_db(school_general_quota)

    global sport_free_quota, sport_used_quota, sport_with_team, sport_with_substitute
    sport_free_quota = models_sport_competition.Sport(
        id=uuid.uuid4(),
        name="Free Quota Sport",
        team_size=1,
        substitute_max=0,
        active=True,
        sport_category=None,
    )
    await add_object_to_db(sport_free_quota)
    sport_used_quota = models_sport_competition.Sport(
        id=uuid.uuid4(),
        name="Used Quota Sport",
        team_size=1,
        substitute_max=0,
        active=True,
        sport_category=None,
    )
    await add_object_to_db(sport_used_quota)
    sport_with_team = models_sport_competition.Sport(
        id=uuid.uuid4(),
        name="Sport with Team",
        team_size=5,
        substitute_max=0,
        active=True,
        sport_category=None,
    )
    await add_object_to_db(sport_with_team)
    sport_with_substitute = models_sport_competition.Sport(
        id=uuid.uuid4(),
        name="Sport with Substitute",
        team_size=5,
        substitute_max=2,
        active=True,
        sport_category=None,
    )
    await add_object_to_db(sport_with_substitute)

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

    global team1, team2
    team1 = models_sport_competition.CompetitionTeam(
        id=uuid.uuid4(),
        sport_id=sport_with_team.id,
        school_id=SchoolType.centrale_lyon.value,
        edition_id=active_edition.id,
        name="Team 1",
        captain_id=sport_manager_user.id,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(team1)
    team2 = models_sport_competition.CompetitionTeam(
        id=uuid.uuid4(),
        sport_id=sport_with_team.id,
        school_id=school1.id,
        edition_id=active_edition.id,
        name="Team 2",
        captain_id=school_bds_user.id,
        created_at=datetime.now(UTC),
    )
    await add_object_to_db(team2)

    global participant1, participant2
    participant1 = models_sport_competition.CompetitionParticipant(
        user_id=admin_user.id,
        school_id=SchoolType.centrale_lyon.value,
        edition_id=active_edition.id,
        sport_id=sport_free_quota.id,
        team_id=None,
        substitute=False,
        license="1234567890",
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
    )
    await add_object_to_db(participant2)


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
        id=uuid.uuid4(),
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
        id=uuid.uuid4(),
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

    client.post(
        f"/competition/editions/{active_edition.id}/inscription",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=False,
    )


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
            "inscription_enabled": False,
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
    assert updated_school["active"] is True
    assert updated_school["inscription_enabled"] is False


async def test_patch_school_extension_as_admin(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/competition/schools/{school1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "from_lyon": True,
            "active": False,
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
    assert updated_school["active"] is False
    assert updated_school["inscription_enabled"] is True


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

    school = client.get(
        f"/competition/schools/{school2.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert school.status_code == 200, school.json()
    school_json = school.json()
    assert school_json["general_quota"] is None, school_json


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

    school = client.get(
        f"/competition/schools/{school2.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert school.status_code == 200, school.json()
    school_json = school.json()
    assert school is not None, school_json
    assert school_json["general_quota"] is not None, school_json
    assert school_json["general_quota"]["athlete_quota"] == 10, school_json
    assert school_json["general_quota"]["cameraman_quota"] == 5, school_json
    assert school_json["general_quota"]["pompom_quota"] == 3, school_json
    assert school_json["general_quota"]["fanfare_quota"] == 2, school_json


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

    school = client.get(
        f"/competition/schools/{school1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert school.status_code == 200, school.json()
    school_json = school.json()
    assert school_json["general_quota"] is not None, school_json
    assert school_json["general_quota"]["athlete_quota"] == 1, school_json
    assert school_json["general_quota"]["cameraman_quota"] == 1, school_json
    assert school_json["general_quota"]["pompom_quota"] == 1, school_json
    assert school_json["general_quota"]["fanfare_quota"] == 1, school_json


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

    school = client.get(
        f"/competition/schools/{school1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert school.status_code == 200, school.json()
    school_json = school.json()
    assert school_json["general_quota"] is not None, school_json
    assert school_json["general_quota"]["athlete_quota"] == 5, school_json
    assert school_json["general_quota"]["cameraman_quota"] == 3, school_json
    assert school_json["general_quota"]["pompom_quota"] == 2, school_json
    assert school_json["general_quota"]["fanfare_quota"] == 1, school_json


async def test_get_school_sport_quota(
    client: TestClient,
) -> None:
    response = client.get(
        f"/competition/schools/{school1.id}/quotas",
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
        f"/competition/schools/{school2.id}/quotas",
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
        f"/competition/schools/{school2.id}/quotas",
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
        f"/competition/schools/{school1.id}/quotas",
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
        f"/competition/schools/{school2.id}/quotas",
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
        f"/competition/schools/{school1.id}/quotas",
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
        f"/competition/schools/{school2.id}/quotas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quota.status_code == 200, quota.json()
    quota_json = quota.json()
    sport_quota = next(
        (q for q in quota_json if q["sport_id"] == str(sport_free_quota.id)),
        None,
    )
    assert sport_quota is None, quota_json


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
