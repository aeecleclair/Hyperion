from datetime import date, datetime, timedelta
from random import randint
from typing import TypedDict

import pytest_asyncio
from pytest import mark
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.modules.elocaps import models_elocaps
from app.modules.elocaps.types_elocaps import CapsMode
from tests.commons import (
    TestingSessionLocal,
    add_object_to_db,
    client,
    create_api_access_token,
    create_user_with_groups,
    event_loop,  # noqa
)


class UserTest(TypedDict):
    user: models_core.CoreUser
    token: str
    players: dict[CapsMode, models_elocaps.Player]
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
        win = randint(-1, 1)
        one_game_players = [
            models_elocaps.GamePlayer(
                game_id=game.id,
                player_id=users[randint(0, 2)]["players"][CapsMode.CD].id,
                team=1,
                score=win,
            ),
            models_elocaps.GamePlayer(
                game_id=game.id,
                player_id=users[3]["players"][CapsMode.CD].id,
                team=2,
                score=-win,
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
                    selectinload(models_elocaps.GamePlayer.player),
                ),
            )
        )
        .scalars()
        .all(),
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
        [i for i in games if i.timestamp.date() == today],
    )
    assert response2.status_code == 200 and len(response2.json()) == len(
        [i for i in games if i.timestamp.date() == yesterday],
    )


def test_get_game():
    game = games[1]
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
    game = games[2]
    tokens = [
        u["token"]
        for i in game_players
        if i.game_id == game.id
        for u in users
        if u["user"].id == i.user_id
    ]
    another_token = next(x for x in users if x["token"] not in tokens)["token"]
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
        == 201
    )
    assert (
        client.post(
            f"/elocaps/games/{game.id}/validate",
            headers={"Authorization": f"Bearer {tokens[1]}"},
        ).status_code
        == 201
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


@mark.parametrize("player_nb", range(4))
def test_player_games(player_nb: int):
    user = users[player_nb]
    response = client.get(
        f"/elocaps/players/{user['user'].id}/games",
        headers={"Authorization": f"Bearer {user['token']}"},
    )
    assert response.status_code == 200 and len(response.json()) == len(
        [i for i in game_players if i.user_id == user["user"].id],
    )


@mark.parametrize("player_nb", range(4))
def test_player_info(player_nb: int):
    response = client.get(
        f"/elocaps/players/{users[player_nb]['user'].id}",
        headers={"Authorization": f"Bearer {users[player_nb]['token']}"},
    )
    assert response.status_code == 200


def test_leaderboard():
    response = client.get(
        "/elocaps/leaderboard?mode=cd",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 200


def test_cancel_game():
    game = games[3]
    tokens = [
        u["token"]
        for i in game_players
        if i.game_id == game.id
        for u in users
        if u["user"].id == i.user_id
    ]
    assert (
        client.post(
            f"/elocaps/games/{game.id}/cancel",
            headers={"Authorization": f"Bearer {tokens[0]}"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/elocaps/games/{game.id}/validate",
            headers={"Authorization": f"Bearer {tokens[1]}"},
        ).status_code
        == 400
    )
    game = games[4]
    tokens = [
        u["token"]
        for i in game_players
        if i.game_id == game.id
        for u in users
        if u["user"].id == i.user_id
    ]
    assert (
        client.post(
            f"/elocaps/games/{game.id}/validate",
            headers={"Authorization": f"Bearer {tokens[0]}"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/elocaps/games/{game.id}/validate",
            headers={"Authorization": f"Bearer {tokens[1]}"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/elocaps/games/{game.id}/cancel",
            headers={"Authorization": f"Bearer {tokens[1]}"},
        ).status_code
        == 400
    )


def test_create_game():
    assert (
        client.post(
            "/elocaps/games",
            headers={"Authorization": f"Bearer {users[0]['token']}"},
            json={
                "mode": CapsMode.SINGLE,
                "players": [
                    {"user_id": users[0]["user"].id, "team": 1, "score": 1},
                    {"user_id": newUser.id, "team": 2, "score": -1},
                ],
            },
        ).status_code
        == 201
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
        )["score"]
        == -1
        and game_player["elo_gain"] is not None
    )
    assert (
        client.post(
            "/elocaps/games",
            headers={"Authorization": f"Bearer {users[0]['token']}"},
            json={
                "mode": CapsMode.SINGLE,
                "players": [
                    {"user_id": users[0]["user"].id, "team": 1, "score": 1},
                    {"user_id": users[0]["user"].id, "team": 2, "score": -1},
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
                    {"user_id": users[0]["user"].id, "team": 1, "score": 1},
                    {"user_id": users[1]["user"].id, "team": 2, "score": -1},
                ],
            },
        ).status_code
        == 400
    )
    # The test below works only with postgresql

    # assert (
    #     client.post(
    #         "/elocaps/games",
    #         headers={"Authorization": f"Bearer {users[2]['token']}"},
    #         json={
    #             "mode": CapsMode.SINGLE,
    #             "players": [
    #                 {"user_id": "baguette", "team": 1, "score": 1},
    #                 {"user_id": users[2]["user"].id, "team": 2, "score": -1},
    #             ],
    #         },
    #     ).status_code
    #     == 400
    # )
