from datetime import date, datetime, timedelta
from random import randint
from typing import TypedDict

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import models_core, models_elocaps
from app.utils.types.elocaps_types import CapsMode
from app.utils.types.groups_type import GroupType
from tests.commons import event_loop  # noqa
from tests.commons import (
    TestingSessionLocal,
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
)

UserTest = TypedDict(
    "UserTest",
    {
        "user": models_core.CoreUser,
        "token": str,
        "players": dict[CapsMode, models_elocaps.Player],
    },
)
users: list[UserTest] = []
newUser: models_core.CoreUser | None = None
game_players: list[models_elocaps.GamePlayer] = []
games: list[models_elocaps.Game] = []


async def create_games(db, n):
    for mode in CapsMode:
        for user in users:
            player = models_elocaps.Player(user_id=user["user"].id, mode=mode)
            await add_object_to_db(player)
            user["players"][mode] = player
    await db.commit()
    for i in range(n):
        game = models_elocaps.Game(
            mode=CapsMode.CD,
            timestamp=datetime.today() - timedelta(hours=2, minutes=randint(0, 4320)),
        )
        games.append(game)
        db.add(game)
        await db.commit()
        quarters = randint(0, 96)
        one_game_players = [
            models_elocaps.GamePlayer(
                game_id=game.id,
                player_id=users[randint(0, 2)]["players"][CapsMode.CD].id,
                team=1,
                quarters=quarters,
            ),
            models_elocaps.GamePlayer(
                game_id=game.id,
                player_id=users[3]["players"][CapsMode.CD].id,
                team=2,
                quarters=96 - quarters,
            ),
        ]
        db.add_all(one_game_players)
        # game_players.extend(one_game_players)
        await db.commit()
    game_players.clear()
    game_players.extend(
        (
            await db.execute(
                select(models_elocaps.GamePlayer).options(
                    selectinload(models_elocaps.GamePlayer.player)
                )
            )
        )
        .scalars()
        .all()
    )


@pytest_asyncio.fixture(scope="module", autouse=True)
async def initialize_the_things_that_are_needed_for_the_tests():
    async with TestingSessionLocal() as db:
        for i in range(4):
            user = await create_user_with_groups([GroupType.student])
            token = create_api_access_token(user)
            users.append({"user": user, "token": token, "players": {}})
        await create_games(db, 100)
        global newUser
        newUser = await create_user_with_groups([GroupType.student])


def test_get_latest_games():
    response = client.get(
        "/elocaps/games/latest/",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 200
    json = response.json()
    assert len(json) == min(10, len(games)) and len(json[0]["game_players"]) == 2


def test_get_games_played_on():
    today = date.today()
    yesterday = today - timedelta(days=1)
    response1 = client.get(
        f"/elocaps/games?time={today.isoformat()}",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    response2 = client.get(
        f"/elocaps/games?time={yesterday.isoformat()}",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response1.status_code == 200 and len(response1.json()) == len(
        [i for i in games if i.timestamp.date() == today]
    )
    assert response2.status_code == 200 and len(response2.json()) == len(
        [i for i in games if i.timestamp.date() == yesterday]
    )


def test_get_game():
    game = games[len(games) // 2]
    response = client.get(
        f"/elocaps/games/{game.id}",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 200
    json = response.json()
    assert json["id"] == game.id
    assert json["timestamp"] == game.timestamp.isoformat()
    assert (
        client.get(
            "/elocaps/games/1234",
            headers={"Authorization": f"Bearer {users[0]['token']}"},
        ).status_code
        == 404
    )


def test_validate_and_end_game():
    game = games[0]
    tokens = [
        u["token"]
        for i in game_players
        if i.game_id == game.id
        for u in users
        if u["user"].id == i.user_id
    ]
    another_token = next(x for x in users if not x["token"] in tokens)["token"]
    assert (
        client.post(
            f"/elocaps/games/{game.id}/validate",
            headers={"Authorization": f"Bearer {another_token}"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/elocaps/games/{game.id}/validate",
            headers={"Authorization": f"Bearer {tokens[0]}"},
        ).status_code
        == 204
    )
    assert (
        client.post(
            f"/elocaps/games/{game.id}/validate",
            headers={"Authorization": f"Bearer {tokens[1]}"},
        ).status_code
        == 204
    )
    response = client.get(
        f"/elocaps/games/{game.id}",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert (
        response.status_code == 200
        and response.json()["id"] == game.id
        and response.json()["is_confirmed"]
    )


def test_get_waiting_games():
    response = client.get(
        "/elocaps/games/waiting",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 200


def test_player_games():
    for i in range(4):
        user = users[0]
        response = client.get(
            f"/elocaps/players/{user['user'].id}/games",
            headers={"Authorization": f"Bearer {user['token']}"},
        )
        assert response.status_code == 200 and len(response.json()) == len(
            [i for i in game_players if i.user_id == user["user"].id]
        )


def test_player_info():
    for i in range(4):
        response = client.get(
            f"/elocaps/players/{users[i]['user'].id}",
            headers={"Authorization": f"Bearer {users[i]['token']}"},
        )
        assert response.status_code == 200


def test_leaderboard():
    response = client.get(
        "/elocaps/leaderboard?mode=cd",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 200


def test_create_game():
    assert (
        client.post(
            "/elocaps/games",
            headers={"Authorization": f"Bearer {users[0]['token']}"},
            json={
                "mode": CapsMode.SINGLE,
                "players": [
                    {"user_id": users[0]["user"].id, "team": 1, "quarters": 1},
                    {"user_id": newUser.id, "team": 2, "quarters": 95},
                ],
            },
        ).status_code
        == 204
    )
    response = client.get(
        "/elocaps/games/latest",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert (
        response.status_code == 200
        and (
            game_player := next(
                i for i in response.json()[0]["game_players"] if i["team"] == 2
            )
        )["quarters"]
        == 95
        and game_player["elo_gain"] is not None
    )
    assert (
        client.post(
            "/elocaps/games",
            headers={"Authorization": f"Bearer {users[0]['token']}"},
            json={
                "mode": CapsMode.SINGLE,
                "players": [
                    {"user_id": users[0]["user"].id, "team": 1, "quarters": 1},
                    {"user_id": users[0]["user"].id, "team": 2, "quarters": 95},
                ],
            },
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/elocaps/games",
            headers={"Authorization": f"Bearer {users[2]['token']}"},
            json={
                "mode": CapsMode.SINGLE,
                "players": [
                    {"user_id": users[0]["user"].id, "team": 1, "quarters": 1},
                    {"user_id": users[1]["user"].id, "team": 2, "quarters": 95},
                ],
            },
        ).status_code
        == 400
    )
