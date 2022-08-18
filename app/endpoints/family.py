# https://fastapi.tiangolo.com/advanced/websockets/#handling-disconnections-and-multiple-clients


import queue
import threading
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.dependencies import is_user_a_member, is_user_a_member_of
from app.models import models_core

from ..utils.types.groups_type import GroupType

router = APIRouter()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket):
        # self.active_connections.remove(websocket)
        pass

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


sg_queue: queue.Queue = queue.Queue()

# https://docs.python.org/3/library/queue.html#queue-objects


class SGRequest(BaseModel):
    """Base schema for user's model"""

    family_id: str
    fillot_id: str


class Fillot(BaseModel):
    """Base schema for user's model"""

    fillot_id: str
    sged: bool = False
    family_id: str | None = None


class Family(BaseModel):
    """Base schema for user's model"""

    family_id: str
    fillot_ids: list[str] = []


# To populate
fillots: dict[str, Fillot] = {}
# To let empty
families: dict[str, Family] = {}

MAX_SIZE = 10


def worker():
    while True:
        sg_request: SGRequest = sg_queue.get()
        print(f"Working on {sg_request}")

        if sg_request.family_id not in families:
            # We create the family
            families[sg_request.family_id] = Family(family_id=sg_request.family_id)

        fillot: Fillot = fillots.get(sg_request.fillot_id, None)

        if fillot is None:
            print("Invalid fillot id")

        elif fillot.sged:
            print("Already sged fillot")

        elif len(families[sg_request.family_id].fillot_ids) >= MAX_SIZE:
            print("Max")

        else:
            print("New fillot")
            fillot.sged = True
            fillot.family_id = sg_request.family_id

            families[sg_request.family_id].fillot_ids.append(sg_request.fillot_id)
            len(families[sg_request.family_id].fillot_ids)

        print(f"Finished {sg_request}")
        sg_queue.task_done()


# Turn-on the worker thread.
threading.Thread(target=worker, daemon=True).start()


manager = ConnectionManager()


@router.get("/html")
async def get():
    return HTMLResponse(html)


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.family)),
):
    await manager.connect(websocket=websocket, user_id=user.id)

    try:
        while True:
            data = await websocket.receive_json()

            if (
                "command" in data
                and data["command"] == "SGRequest"
                and "fillot_id" in data
            ):
                sg_request = SGRequest(family_id=user.id, fillot_id=data["fillot_id"])
                sg_queue.put(sg_request)
            else:
                pass
                # Send error

            # await manager.send_personal_message(f"You wrote: {data}", websocket)
            # await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("Client #{client_id} left the chat")
