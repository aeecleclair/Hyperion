from typing import TypedDict
from datetime import datetime, timedelta, date
from random import randint

from app.main import app
from app.models import models_core, models_elocaps
from app.utils.types.groups_type import GroupType
from app.utils.types.elocaps_types import CapsMode
from tests.commons import (
    TestingSessionLocal,
    client,
    create_api_access_token,
    create_user_with_groups,
)

UserTest = TypedDict("UserTest", {"user": models_core.CoreUser, "token": str})
users: list[UserTest] = []
game_players: list[models_elocaps.GamePlayer] = []
games: list[models_elocaps.Game] = []


async def create_games(db, n):
    for i in range(n):
        game = models_elocaps.Game(
            mode=CapsMode.CD,
            timestamp=datetime.today() - timedelta(hours=2, minutes=randint(0, 4320)),
        )
        games.append(game)
        db.add(game)
        await db.commit()
        quarters = randint(0, 96)
        players = [
            models_elocaps.GamePlayer(
                game_id=game.id,
                user_id=users[randint(0, 2)]["user"].id,
                team=1,
                quarters=quarters,
            ),
            models_elocaps.GamePlayer(
                game_id=game.id,
                user_id=users[3]["user"].id,
                team=2,
                quarters=96 - quarters,
            ),
        ]
        db.add_all(players)
        game_players.extend(players)
        await db.commit()


@app.on_event("startup")  # create the data needed in the tests
async def startuptest():
    async with TestingSessionLocal() as db:
        for i in range(4):
            user = await create_user_with_groups([GroupType.student], db)
            token = create_api_access_token(user)
            users.append({"user": user, "token": token})
        await create_games(db, 100)


def test_get_latest_games():
    response = client.get(
        "/elocaps/games/latest/",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 200
    json = response.json()
    assert len(json) == min(10, len(games)) and len(json[0]["players"]) == 2


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
    print(games[0].id)


def test_get_game():
    game = games[len(games) // 2]
    response = client.get(
        f"/elocaps/games/{game.id}",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 200
    json = response.json()
    assert json["timestamp"] == game.timestamp.isoformat() and json["id"] == game.id


def test_validate_game():
    response = client.get(
        f"/elocaps/games/{games[0].id}",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 200


def test_my_games():
    response = client.get(
        "/elocaps/players/me/games",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 200 and len(response.json()) == len(
        [i for i in game_players if i.user_id == users[0]["user"].id]
    )


def test_my_info():
    response = client.get(
        "/elocaps/players/me", headers={"Authorization": f"Bearer {users[0]['token']}"}
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
        "/elocaps/leaderboard?mode=1",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    assert response.status_code == 200


def test_create_game():
    response = client.post(
        "/elocaps/games",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
        json={
            "mode": CapsMode.SINGLE,
            "players": [
                {"user_id": users[0]["user"].id, "team": 1, "quarters": 1},
                {"user_id": users[1]["user"].id, "team": 2, "quarters": 95},
            ],
        },
    )
    assert response.status_code == 204
    response = client.get(
        "/elocaps/games/latest",
        headers={"Authorization": f"Bearer {users[0]['token']}"},
    )
    print(response.json()[0])
    assert (
        response.status_code == 200
        and next(i["quarters"] for i in response.json()[0]["players"] if i["team"] == 2)
        == 95
    )
