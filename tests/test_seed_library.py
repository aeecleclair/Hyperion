import uuid
from datetime import UTC, datetime

import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.modules.seed_library import models_seed_library, types_seed_library
from tests.commons import (
    add_object_to_db,
    create_api_access_token,
    create_user_with_groups,
)

admin_user: models_users.CoreUser
simple_user: models_users.CoreUser
species1: models_seed_library.Species
species2: models_seed_library.Species
plant_ancestor_from_1: models_seed_library.Plant
plant_from_1: models_seed_library.Plant
plant_from_2: models_seed_library.Plant
plant_from_1_update_test: models_seed_library.Plant
plant_from_2_update_test: models_seed_library.Plant


token_simple: str
token_admin: str


@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_objects() -> None:
    global \
        admin_user, \
        simple_user, \
        species1, \
        species2, \
        plant_from_1, \
        plant_from_2, \
        plant_ancestor_from_1, \
        plant_from_1_update_test, \
        plant_from_2_update_test, \
        token_simple, \
        token_admin

    admin_user = await create_user_with_groups([GroupType.seed_library])

    simple_user = await create_user_with_groups(
        [],
    )

    token_simple = create_api_access_token(simple_user)
    token_admin = create_api_access_token(admin_user)

    species1 = models_seed_library.Species(
        id=uuid.uuid4(),
        prefix="ROM",
        species_name="Romarin",
        difficulty=2,
        card="description or URL",
        nb_seeds_recommended=15,
        species_type=types_seed_library.SpeciesType.aromatic,
        start_season=datetime(2025, 10, 1, tzinfo=UTC),
        end_season=datetime(2025, 12, 1, tzinfo=UTC),
        time_maturation=55,
    )

    await add_object_to_db(species1)

    species2 = models_seed_library.Species(
        id=uuid.uuid4(),
        prefix="ORC",
        species_name="Orchidée",
        difficulty=3,
        card="description or URL",
        nb_seeds_recommended=1,
        species_type=types_seed_library.SpeciesType.ornamental,
        start_season=datetime(2025, 5, 1, tzinfo=UTC),
        end_season=datetime(2025, 9, 1, tzinfo=UTC),
        time_maturation=24,
    )

    await add_object_to_db(species2)

    plant_ancestor_from_1 = models_seed_library.Plant(
        id=uuid.uuid4(),
        state=types_seed_library.PlantState.retrieved,
        species_id=species1.id,
        propagation_method=types_seed_library.PropagationMethod.seed,
        nb_seeds_envelope=18,
        plant_reference="ROM27022024001",
        ancestor_id=None,
        previous_note=None,
        current_note="this is my new note",
        borrower_id=simple_user.id,
        confidential=True,
        nickname="Tom",
        planting_date=datetime.now(tz=UTC),
        borrowing_date=datetime.now(tz=UTC),
    )

    await add_object_to_db(plant_ancestor_from_1)

    plant_from_1 = models_seed_library.Plant(
        id=uuid.uuid4(),
        state=types_seed_library.PlantState.waiting,
        species_id=species1.id,
        propagation_method=types_seed_library.PropagationMethod.seed,
        nb_seeds_envelope=12,
        plant_reference="ROM27022025001",
        ancestor_id=plant_ancestor_from_1.id,
        previous_note="this is my ancestor note",
        current_note=None,
        borrower_id=None,
        confidential=False,
        nickname=None,
        planting_date=None,
        borrowing_date=None,
    )

    await add_object_to_db(plant_from_1)

    plant_from_2 = models_seed_library.Plant(
        id=uuid.uuid4(),
        state=types_seed_library.PlantState.retrieved,
        species_id=species2.id,
        propagation_method=types_seed_library.PropagationMethod.cutting,
        nb_seeds_envelope=18,
        plant_reference="ORC27022025001",
        ancestor_id=None,
        previous_note=None,
        current_note="this is my new note",
        borrower_id=simple_user.id,
        confidential=False,
        nickname=None,
        planting_date=datetime.now(tz=UTC),
        borrowing_date=datetime.now(tz=UTC),
    )

    await add_object_to_db(plant_from_2)

    plant_from_2_update_test = models_seed_library.Plant(
        id=uuid.uuid4(),
        state=types_seed_library.PlantState.retrieved,
        species_id=species2.id,
        propagation_method=types_seed_library.PropagationMethod.cutting,
        nb_seeds_envelope=23,
        plant_reference="ORC27022025002",
        ancestor_id=plant_from_2.id,
        previous_note=None,
        current_note="...",
        borrower_id=simple_user.id,
        confidential=False,
        nickname=None,
        planting_date=datetime.now(tz=UTC),
        borrowing_date=datetime.now(tz=UTC),
    )

    await add_object_to_db(plant_from_2_update_test)

    plant_from_1_update_test = models_seed_library.Plant(
        id=uuid.uuid4(),
        state=types_seed_library.PlantState.waiting,
        species_id=species1.id,
        propagation_method=types_seed_library.PropagationMethod.seed,
        nb_seeds_envelope=212,
        plant_reference="ROM27022025001",
        ancestor_id=plant_from_1.id,
        previous_note=None,
        current_note="...",
        borrower_id=None,
        confidential=False,
        nickname=None,
        planting_date=datetime.now(tz=UTC),
        borrowing_date=datetime.now(tz=UTC),
    )

    await add_object_to_db(plant_from_1_update_test)


# ---------------------------------------------------------------------------- #
#                              Get tests                                       #
# ---------------------------------------------------------------------------- #
def test_get_all_species(client: TestClient):
    response = client.get(
        "/seed_library/species/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_all_species_types(client: TestClient):
    response = client.get(
        "/seed_library/species/types",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 8


def test_get_waiting_plants(client: TestClient):
    response = client.get(
        "/seed_library/plants/waiting",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    plants = response.json()
    assert len(plants) == 2
    plant0 = plants[0]
    assert plant0["id"] == plant_from_1.id


def test_get_my_plants(client: TestClient):
    response = client.get(
        "/seed_library/plants/users/me",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    plants = response.json()
    assert len(plants) == 3

    plants_id = [plant["id"] for plant in plants]
    assert plant_ancestor_from_1.id in plants_id
    assert plant_from_2.id in plants_id


def test_get_plants_by_user_id_as_simple(client: TestClient):
    response = client.get(
        f"/seed_library/plants/users/{simple_user.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_get_plants_by_user_id_as_admin(client: TestClient):
    response = client.get(
        f"/seed_library/plants/users/{simple_user.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 200
    plants = response.json()
    assert len(plants) == 3

    plants_id = [plant["id"] for plant in plants]
    assert plant_ancestor_from_1.id in plants_id
    assert plant_from_2.id in plants_id


def test_get_plant_by_known_id(client: TestClient):
    response = client.get(
        f"/seed_library/plants/{plant_from_1.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()["id"] == plant_from_1.id


def test_get_plant_by_non_unknown_id(client: TestClient):
    response = client.get(
        f"/seed_library/plants/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 404


def test_get_information(client: TestClient):
    response = client.get(
        "/seed_library/information",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------- #
#                              Post tests                                       #
# ---------------------------------------------------------------------------- #


def test_create_species_as_simple(client: TestClient):
    response = client.post(
        "/seed_library/species/",
        json={
            "prefix": "TOM",
            "species_name": "Tomate",
            "difficulty": 1,
            "card": "https://fr.wikipedia.org/wiki/Tomate",
            "nb_seeds_recommended": 8,
            "species_type": types_seed_library.SpeciesType.vegetables,
            "time_maturation": 12,
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_create_species_used_prefix_as_admin(client: TestClient):
    response = client.post(
        "/seed_library/species/",
        json={
            "prefix": "ROM",
            "species_name": "Tomate",
            "difficulty": 1,
            "card": "https://fr.wikipedia.org/wiki/Tomate",
            "nb_seeds_recommended": 8,
            "species_type": types_seed_library.SpeciesType.vegetables,
            "time_maturation": 12,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


def test_create_species_used_name_as_admin(client: TestClient):
    response = client.post(
        "/seed_library/species/",
        json={
            "prefix": "TOM",
            "species_name": "Romarin",
            "difficulty": 1,
            "card": "https://fr.wikipedia.org/wiki/Tomate",
            "nb_seeds_recommended": 8,
            "species_type": types_seed_library.SpeciesType.vegetables,
            "time_maturation": 12,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


def test_create_species_impossible_difficulty_as_admin(client: TestClient):
    response = client.post(
        "/seed_library/species/",
        json={
            "prefix": "TOM",
            "species_name": "Tomate",
            "difficulty": 7,
            "card": "https://fr.wikipedia.org/wiki/Tomate",
            "nb_seeds_recommended": 8,
            "species_type": types_seed_library.SpeciesType.vegetables,
            "time_maturation": 12,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 400


def test_create_species_as_admin(client: TestClient):
    response = client.post(
        "/seed_library/species/",
        json={
            "prefix": "TOM",
            "species_name": "Tomate",
            "difficulty": 1,
            "card": "https://fr.wikipedia.org/wiki/Tomate",
            "nb_seeds_recommended": 8,
            "species_type": types_seed_library.SpeciesType.vegetables,
            "time_maturation": 12,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    assert len(response.json()) == 1

    ###############Vérif################

    response_get = client.get(
        "/seed_library/species/",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response_get.status_code == 200
    assert len(response_get.json()) == 3


def test_create_plant_without_ancestor_as_simple(client: TestClient):
    response = client.post(
        "/seed_library/plants/",
        json={
            "species_id": species1.id,
            "propagation_method": types_seed_library.PropagationMethod.seed,
            "nb_seeds_envelope": 3,
            # "ancestor_id": None,
            "previous_note": "Oskour maman j ai tué ma plante",
            "confidential": False,
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_create_plant_without_ancestor_as_admin(client: TestClient):
    response = client.post(
        "/seed_library/plants/",
        json={
            "species_id": species1.id,
            "propagation_method": types_seed_library.PropagationMethod.seed,
            "nb_seeds_envelope": 3,
            "ancestor_id": None,
            "previous_note": "Oskour maman j ai tué ma plante",
            "confidential": False,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 201
    assert len(response.json()) == 1
    assert response.json()["id"] == plant_from_1.id

    ###############Vérif################

    response_get = client.get(
        "/seed_library/plants/waiting",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response_get.status_code == 200
    assert len(response_get.json()) == 3
    assert len(response_get.json()["plant_reference"]) == 12
    assert len(response_get.json()["id"]) != plant_from_1.id


def test_create_plant_with_ancestor(client: TestClient):
    response = client.post(
        "/seed_library/plants/",
        json={
            "species_id": species1.id,
            "propagation_method": types_seed_library.PropagationMethod.seed,
            "nb_seeds_envelope": 3,
            "ancestor_id": plant_from_1.id,
            "previous_note": "Oskour maman j ai tué ma plante",
            "confidential": False,
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 201
    assert len(response.json()) == 1
    assert response.json()["id"] == plant_from_1.id

    ###############Vérif################

    response_get = client.get(
        "/seed_library/plants/waiting",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response_get.status_code == 200
    assert len(response_get.json()) == 4
    assert len(response_get.json()["plant_reference"]) == 12
    assert len(response_get.json()["id"]) != plant_from_1.id


def test_create_plant_without_species(client: TestClient):
    response = client.post(
        "/seed_library/plants/",
        json={
            "species_id": uuid.uuid4(),
            "propagation_method": types_seed_library.PropagationMethod.seed,
            "nb_seeds_envelope": 5,
            "ancestor_id": plant_from_1.id,
            "previous_note": "Oskour maman j ai tué ma plante",
            "confidential": False,
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------- #
#                              Patch tests                                     #
# ---------------------------------------------------------------------------- #


def test_update_species_as_simple(client: TestClient):
    response = client.patch(
        f"/seed_library/species/{species1.id}",
        json={
            "prefix": "DAT",
            "difficulty": 2,
            "card": "https://fr.wiktionary.org/wiki/dat%C3%A9",
            "nb_seeds_recommended": 48,
            "start_season": datetime(2025, 10, 1, tzinfo=UTC),
            "end_season": datetime(2025, 12, 1, tzinfo=UTC),
            "time_maturation": 6,
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 400


def test_update_unknown_species(client: TestClient):
    response = client.patch(
        f"/seed_library/species/{uuid.uuid4()}",
        json={
            "prefix": "DAT",
            "difficulty": 2,
            "card": "https://fr.wiktionary.org/wiki/dat%C3%A9",
            "nb_seeds_recommended": 48,
            "start_season": datetime(2025, 10, 1, tzinfo=UTC),
            "end_season": datetime(2025, 12, 1, tzinfo=UTC),
            "time_maturation": 6,
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 400


def test_update_species_as_admin(client: TestClient):
    ##############Plant creation###############
    response_create = client.post(
        "/seed_library/species/",
        json={
            "prefix": "UPD",
            "species_name": "Update",
            "difficulty": 1,
            "card": "https://fr.wikipedia.org/wiki/Mise_%C3%A0_jour",
            "nb_seeds_recommended": 11,
            "species_type": types_seed_library.SpeciesType.interior,
            "time_maturation": 3,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response_create.status_code == 201
    ###########Check create+get id#############
    response_get = client.get(
        "/seed_library/species/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response_get.status_code == 200
    assert len(response_get.json()) == 4
    test = False
    for s in response_get.json():
        if s["species_name"] == "Update":
            test = True
            new_id = s["id"]
    assert test

    ################Modification################
    response = client.patch(
        f"/seed_library/species/{new_id}",
        json={
            "prefix": "DAT",
            "difficulty": 2,
            "card": "https://fr.wiktionary.org/wiki/dat%C3%A9",
            "nb_seeds_recommended": 48,
            "start_season": datetime(2025, 10, 1, tzinfo=UTC),
            "end_season": datetime(2025, 12, 1, tzinfo=UTC),
            "time_maturation": 6,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204
    ############## Check Update ###############
    response_updated_get = client.get(
        "/seed_library/species/",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response_updated_get.status_code == 200
    test = False
    for s in response_get.json():
        if s["id"] == new_id:
            assert s["prefix"] == "DAT"
            assert s["difficulty"] == 2
            assert s["card"] == "https://fr.wiktionary.org/wiki/dat%C3%A9"
            assert s[""] == 48
            test = True
    assert test


def test_update_plant_not_as_owner(client: TestClient):
    pd = datetime(2002, 1, 1, tzinfo=UTC)
    bd = datetime(2002, 2, 1, tzinfo=UTC)
    response = client.patch(
        f"/seed_library/plants/{plant_from_2_update_test.id}",
        json={
            "state": types_seed_library.PlantState.used_up,
            "current_note": "plant successfully modified",
            "confidential": False,
            "planting_date": pd,
            "borrowing_date": bd,
            "nickname": "your updated plant",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 403


def test_update_unknown_plant(client: TestClient):
    pd = datetime(2003, 1, 1, tzinfo=UTC)
    bd = datetime(2003, 2, 1, tzinfo=UTC)
    response = client.patch(
        f"/seed_library/plants/{uuid.uuid4()}",
        json={
            "state": types_seed_library.PlantState.used_up,
            "current_note": "plant successfully modified",
            "confidential": False,
            "planting_date": pd,
            "borrowing_date": bd,
            "nickname": "your updated plant",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404


def test_update_plant_as_owner(client: TestClient):
    pd = datetime(2001, 1, 1, tzinfo=UTC)
    bd = datetime(2001, 2, 1, tzinfo=UTC)
    response = client.patch(
        f"/seed_library/plants/{plant_from_2_update_test.id}",
        json={
            "state": types_seed_library.PlantState.used_up,
            "current_note": "plant successfully modified",
            "confidential": False,
            "planting_date": pd,
            "borrowing_date": bd,
            "nickname": "your updated plant",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204
    ############## Check Update ###############
    response_updated_get = client.get(
        "/seed_library/plants/{plant_from_2_update_test.id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response_updated_get.status_code == 200
    test = False
    for p in response_updated_get.json():
        if p["id"] == plant_from_2_update_test.id:
            assert p["state"] == types_seed_library.PlantState.used_up
            assert p["current_note"] == "plant successfully modified"
            assert p["confidential"] == False
            assert p["planting_date"] == pd
            assert p["borrowing_date"] == bd
            assert p["nickname"] == "your updated plant"
            test = True
    assert test


def test_update_unknown_plant_admin(client: TestClient):
    pd = datetime(2008, 1, 1, tzinfo=UTC)
    bd = datetime(2008, 2, 1, tzinfo=UTC)
    response = client.patch(
        f"/seed_library/plants/{uuid.uuid4()}/admin",
        json={
            "state": types_seed_library.PlantState.retrieved,
            "current_note": "plant successfully modified",
            "confidential": True,
            "planting_date": pd,
            "borrowing_date": bd,
            "nickname": "updated plant",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 404


def test_update_plant_admin_as_simple(client: TestClient):
    pd = datetime(2000, 1, 1, tzinfo=UTC)
    bd = datetime(2000, 2, 1, tzinfo=UTC)
    response = client.patch(
        f"/seed_library/plants/{plant_from_1.id}/admin",
        json={
            "state": types_seed_library.PlantState.retrieved,
            "current_note": "plant successfully modified",
            "confidential": True,
            "planting_date": pd,
            "borrowing_date": bd,
            "nickname": "updated plant",
        },
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403


def test_update_plant_admin_as_admin(client: TestClient):
    ##############Plant creation###############
    response_create = client.post(
        "/seed_library/plants/",
        json={
            "species_id": species1.id,
            "propagation_method": types_seed_library.PropagationMethod.seed,
            "nb_seeds_envelope": 32,
            "ancestor_id": plant_from_1.id,
            "previous_note": "test_admin_update_plant_admin",
            "confidential": False,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response_create.status_code == 201
    ###########Check create+get id#############
    response_get = client.get(
        "/seed_library/plants/waiting",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response_get.status_code == 200
    assert len(response_get.json()) == 5
    test = False
    for p in response_get.json():
        if p["previous_note"] == "test_admin_update_plant_admin":
            test = True
            new_id = p["id"]
    assert test

    ################Modification################
    pd = datetime(2000, 1, 1, tzinfo=UTC)
    bd = datetime(2000, 2, 1, tzinfo=UTC)
    response = client.patch(
        f"/seed_library/plants/{new_id}/admin",
        json={
            "state": types_seed_library.PlantState.retrieved,
            "current_note": "plant successfully modified",
            "confidential": True,
            "planting_date": pd,
            "borrowing_date": bd,
            "nickname": "updated plant",
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 204
    ############## Check Update ###############
    response_updated_get = client.get(
        "/seed_library/plants/{new_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response_updated_get.status_code == 200
    test = False
    for p in response_get.json():
        if p["id"] == new_id:
            assert p["state"] == types_seed_library.PlantState.retrieved
            assert p["current_note"] == "plant successfully modified"
            assert p["confidential"] == True
            assert p["planting_date"] == pd
            assert p["borrowing_date"] == bd
            assert p["nickname"] == "updated plant"
            test = True
    assert test


def test_unknown_borrow(client: TestClient):
    response = client.patch(
        f"/seed_library/plants/{uuid.uuid4()}/borrow",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 404


def test_borrow(client: TestClient):
    response = client.patch(
        f"/seed_library/plants/{plant_from_1_update_test.id}/borrow",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 204
    ############## Check Update ###############
    response_updated_get = client.get(
        "/seed_library/plants/{plant_from_1_update_test.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response_updated_get.status_code == 200
    test = False
    for p in response_updated_get.json():
        if p["id"] == plant_from_1_update_test.id:
            assert p["borrower_id"] == token_simple
            assert p["borrowing_date"] is not None
            assert p["state"] == types_seed_library.PlantState.retrieved
            test = True
    assert test


# ---------------------------------------------------------------------------- #
#                              Delete tests                                    #
# ---------------------------------------------------------------------------- #


def test_delete_species_simple(client: TestClient):
    response = client.delete(
        f"/seed_library/species/{species1.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403

    species = client.get(
        "/seed_library/species/",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    assert len(species) == 4


def test_delete_species_not_existing(client: TestClient):
    response = client.delete(
        f"/seed_library/species/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404

    species = client.get(
        "/seed_library/species/",
        headers={"Authorization": f"Bearer {token_admin}"},
    ).json()

    assert len(species) == 4


def test_delete_species_admin(client: TestClient):
    response = client.post(
        "/seed_library/species/",
        json={
            "prefix": "Del",
            "species_name": "Delete",
            "difficulty": 5,
            "card": "https://fr.wikipedia.org/wiki/Tomate",
            "nb_seeds_recommended": 8,
            "species_type": types_seed_library.SpeciesType.vegetables,
            "time_maturation": 12,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    assert response.status_code == 201

    species = client.get(
        "/seed_library/species/",
        headers={"Authorization": f"Bearer {token_admin}"},
    ).json()
    assert species.status_code == 200
    assert len(species) == 5

    test = False
    for s in species.json():
        if s["species_name"] == "Delete":
            test = True
            id_delete = s["id"]
    assert test

    response = client.delete(
        f"/seed_library/species/{id_delete}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    assert response.status_code == 204

    species = client.get(
        "/seed_library/species/",
        headers={"Authorization": f"Bearer {token_admin}"},
    ).json()

    assert len(species) == 4


def test_delete_plant_simple(client: TestClient):
    response = client.delete(
        f"/seed_library/plants/{plant_from_1.id}",
        headers={"Authorization": f"Bearer {token_simple}"},
    )
    assert response.status_code == 403

    plants = client.get(
        "/seed_library/plants/waiting",
        headers={"Authorization": f"Bearer {token_simple}"},
    ).json()

    assert len(plants) == 5


def test_delete_plant_not_existing(client: TestClient):
    response = client.delete(
        f"/seed_library/ plants/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert response.status_code == 404

    plants = client.get(
        "/seed_library/plants/waiting",
        headers={"Authorization": f"Bearer {token_admin}"},
    ).json()

    assert len(plants) == 5


def test_delete_plant_admin(client: TestClient):
    response = client.post(
        "/seed_library/plants/",
        json={
            "species_id": species1.id,
            "propagation_method": types_seed_library.PropagationMethod.seed,
            "nb_seeds_envelope": 3,
            "ancestor_id": None,
            "previous_note": "Oskour maman j ai tué ma plante",
            "confidential": False,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    assert response.status_code == 201

    plants = client.get(
        "/seed_library/plants/waiting",
        headers={"Authorization": f"Bearer {token_admin}"},
    ).json()
    assert plants.status_code == 200
    assert len(plants) == 6

    test = False
    for p in plants.json():
        if p["previous_note"] == "Oskour maman j ai tué ma plante":
            test = True
            id_delete = p["id"]
    assert test

    response = client.delete(
        f"/seed_library/plants/{id_delete}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    assert response.status_code == 204

    plants = client.get(
        "/seed_library/plants/waiting",
        headers={"Authorization": f"Bearer {token_admin}"},
    ).json()

    assert len(plants) == 5
