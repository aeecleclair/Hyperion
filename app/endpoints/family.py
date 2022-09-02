import asyncio
import uuid
from datetime import datetime, timedelta
from enum import Enum

import yaml
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter()

"""
The Family module allows to manage sg. 

The client open a websocket with the API allowing for quick bidirectional communication

The API send commands to the client: wait, start the sg, mark a fillot as sged

The client is able to ask 
"""


class SGRequest(BaseModel):
    """
    A sg request is send by the client then added to the queue before being processed by the worker.
    It indicate the interest of the client to sg a fillot.
    """

    family_token: str
    fillot_id: str

    def __str__(self) -> str:
        return f"SGRequest<{self.family_token}: {self.fillot_id}>"


class ExportFillot(BaseModel):
    """
    Fillot representation send by the API to the client.
    For privacy reasons it does not contains the family_token of the family which sged the fillot.
    """

    fillot_id: str
    fillot_name: str
    floor: str
    sged: bool = False


class Fillot(ExportFillot):
    """
    Fillot representation
    """

    # FamilyTokens is a personal identifiers and should not be leaked. It gives rights over this module
    family_token: str | None = None

    def __str__(self) -> str:
        return f"Fillot[{self.fillot_id}]<{self.family_token}; {self.sged}>"


class Family(BaseModel):
    """
    Family representation.
    """

    family_token: str
    name: str
    # How many fillots should the family have at the end of the sg?

    # WARNING TODO: this list contains fillots ?
    # Modify in the ws message method
    fillot_ids: list[str] = []
    # fillots: list[Fillot]

    # Current amount of fillots. Should be updated when a new fillot is added
    nb_fillots: int = 0
    # Dictionary indicating the amount of fillot in a given floor.
    # If there isn't any fillots in the floor, nb_fillots_by_floors[floor] could be inexistant
    nb_fillots_by_floors: dict[str, int] = {}
    # Amount of Fillots that are not in Adoma
    nb_fillots_comparat: int = 0

    def __str__(self) -> str:
        return f"Fillot[{self.family_token}]<{self.fillot_ids}> ({self.nb_fillots})"


class Command(str, Enum):
    """
    A command is a string the API can send to the client
    """

    # The API indicates that the websocket was successfully connected
    connected = "connected"
    # The API indicates that client should start the countdown. A countdown string which will be shown can be provided
    countdown = "countdown"
    # The API indicates that the sg can start
    start = "start"
    # The following commands can be send in response to a sg request
    sg_success = "sg_success"  # The fillot was successfully sged by the family
    sg_failure = "sg_failure"  # The family failed to sg the fillot (because it was already sged, because there is already the maximum amount of fillots...)
    # When a fillot is sged, the API should broadcast a sg_done to indicates that the fillot is now unavailable
    sg_done = "sg_done"

    invalid_token = "invalid_token"


class Message(BaseModel):
    """
    A message contain a command and additional data, which is specific to each command
    """

    command: Command

    def __str__(self) -> str:
        return f"{self.command}"


class CountdownMessage(Message):
    countdown: str

    family_name: str = ""


class StartMessage(Message):
    """
    The start message is send when the sg begin. It can be send when the client open a new websocket if the sg already started
    """

    # List of available fillots, by floor
    fillots: dict[str, list[Fillot]]
    # Ids of the fillots which belong to the family receiving the message
    family_fillots_ids: list[str]
    # Current amount of fillots in the family
    nb_fillots: int
    max_nb_fillots: int
    nb_fillots_comparat: int
    max_nb_fillots_comparat: int
    nb_fillots_by_floors: dict[str, int]
    max_nb_fillots_by_floors: dict[str, int]

    family_name: str = ""


class SGResponseMessage(Message):
    fillot_id: str
    # The name is used to show a message indicating the sg was successful to the client
    fillot_name: str = ""
    # The message can be send by the client to the user. Especially useful for failed sg attempts.
    message: str = ""

    # New data about of the family
    # New amount of fillots
    nb_fillots: int = -1
    nb_fillots_comparat: int = -1
    nb_fillots_by_floors: dict[str, int] = {}


class Status(str, Enum):
    """
    API status: if the sg already started or not
    """

    countdown = "countdown"
    sg = "sg"


class ConnectionManager:
    """
    The connection manager is responsible for managing all websocket
    A dictionary of all websocket is used to send messages.
    """

    def __init__(self):
        # active_connections contains {familyId: websocket}
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, family_token: str) -> None:
        if family_token in self.active_connections:
            # There is already a connected client with this token
            # we want to disconnect it before accepting the new connection
            # to prevent a family from using multiple computers
            await self.active_connections[family_token].close()
            # We don't want to disconnect the websocket here as the function will be called by the ws endpoint

        await websocket.accept()
        self.active_connections[family_token] = websocket
        await self.send_to(
            family_token=family_token,
            message=Message(command=Command.connected),
        )

    def disconnect(self, family_token: str) -> None:
        """
        Warning, this won't close the websocket. This should be called after closing.
        This method should be used in a try, except block

        ```python
        try:
            # Add code here...
        except WebSocketDisconnect:
            manager.disconnect(family_token=family_token)
        ```
        """
        print("Disconnecting", family_token)
        del self.active_connections[family_token]

    async def send_to(self, family_token: str, message: Message):
        print(f"Sending message to {family_token}", message)
        websocket = self.active_connections[family_token]
        await websocket.send_json(message.dict())

    async def send_to_everyone_but(
        self,
        excluded_family_token: str,
        message: Message,
    ) -> None:
        print(f"Sending message to everyone but {excluded_family_token}", message)
        for family_token in self.active_connections:
            if family_token != excluded_family_token:
                await self.active_connections[family_token].send_json(message.dict())

    async def broadcast(self, message: Message):
        for family_token in self.active_connections:
            await self.active_connections[family_token].send_json(message.dict())


"""
When the websocket receive a sg request, they are pushed to this queue.
The websocket is indeed asynchrone, and we want to be sure that sg request are processed in a FIFO order.

When a new item is pushed to the queue, it will be processed by the worker.
"""
# We use an asyncio queue as FastAPI is async and does not support synchronous queue
sg_queue: asyncio.Queue = asyncio.Queue()


# Dict of available Fillots with FillotId as key
fillots: dict[str, Fillot] = {}
# Dict of fillots classed by floor, used by the front end to display results
fillots_by_floor: dict[str, list[Fillot]] = {}
# These two variables are populated using a YAML file


def remove_family_token(
    fillots_by_floor: dict[str, list[Fillot]]
) -> dict[str, list[ExportFillot]]:
    """
    Transform a `list[Fillot]` into a `list[ExportFillot]`
    """
    res = {}
    for floor_name in fillots_by_floor:
        res[floor_name] = [
            ExportFillot(**fillot.dict()) for fillot in fillots_by_floor[floor_name]
        ]
    return res


# Max amount of fillots a family can have
max_nb_fillots: int = 3
# Max amount of fillots by floor a family can have
max_nb_fillots_by_floors: dict[str, int] = {}
# Max amount of fillots that are not in Adoma a family can have
max_nb_fillots_comparat: int = 13
# Key of the floor that is not in Comparat
ADOMA = "Adoma"
# Dict of Family with FamilyToken as key
families: dict[str, Family] = {}

# Datetime of the sg
# TODO remove
startdatetime = datetime.now() + timedelta(seconds=15)


with open("fillots.yaml") as f:
    data = yaml.safe_load(f)

for floor_name in data:
    if floor_name in max_nb_fillots_by_floors:
        raise ValueError(f"Floor {floor_name} is not an unique key in family.ymal")

    max_nb_fillots_by_floors[floor_name] = data[floor_name]["max_nb_fillots"]

    fillots_by_floor[floor_name] = []

    for fillot_name in data[floor_name]["fillots"]:
        fillot_id = str(uuid.uuid4())

        fillot = Fillot(
            fillot_id=fillot_id,
            fillot_name=fillot_name,
            floor=floor_name,
        )
        fillots[fillot_id] = fillot
        fillots_by_floor[floor_name].append(fillot)

with open("families.yaml") as f:
    data = yaml.safe_load(f)

for token in data:
    if token in families:
        raise ValueError(f"Token {token} is not unique in families.yaml")
    families[token] = Family(
        family_token=token,
        name=data[token]["name"],
        fillot_ids=[],
        nb_fillots=0,
        nb_fillots_by_floors={},
        nb_fillots_comparat=0,
    )

manager = ConnectionManager()


class ModuleStatus(BaseModel):
    status: Status = Status.countdown
    # We can lock the module to prevent the worker to be started more than one time
    locked: bool = False


module_status = ModuleStatus()


async def worker():
    # TODO remove
    startdatetime = datetime.now() + timedelta(seconds=15)

    print("Starting worker")

    if module_status.locked:
        print("Exiting, the module is locked")
        return

    module_status.status = Status.countdown
    # We lock the module until the worker stops
    module_status.locked = True

    # We sleep until the time to start the countdown, which is 10 seconds before the sg
    sleep_duration = startdatetime - datetime.now() - timedelta(seconds=10)
    print("Sleeping", sleep_duration.seconds, "seconds")
    await asyncio.sleep(sleep_duration.seconds)

    # We send countdown messages until the starting time
    while datetime.now() < startdatetime:
        seconds = startdatetime - datetime.now()
        seconds_int = seconds.seconds
        print("Countdown:", seconds_int)
        await manager.broadcast(
            message=CountdownMessage(
                command=Command.countdown, countdown=str(seconds_int)
            )
        )
        await asyncio.sleep(1)

    await manager.broadcast(
        message=StartMessage(
            command=Command.start,
            fillots=remove_family_token(fillots_by_floor),
            family_fillots_ids=[],  # At the beginning all families have no fillots
            nb_fillots=0,
            max_nb_fillots=max_nb_fillots,
            nb_fillots_comparat=0,
            max_nb_fillots_comparat=max_nb_fillots_comparat,
            nb_fillots_by_floors={},
            max_nb_fillots_by_floors=max_nb_fillots_by_floors,
        )
    )
    module_status.status = Status.sg

    while True:
        sg_request: SGRequest = await sg_queue.get()
        if sg_request.fillot_id not in fillots:
            pass
            # Send an invalid id message
        fillot = fillots[sg_request.fillot_id]
        if fillot.sged:
            # Send a already sged message
            await manager.send_to(
                family_token=sg_request.family_token,
                message=SGResponseMessage(
                    command=Command.sg_failure,
                    fillot_id=sg_request.fillot_id,
                    message=f"Le fillot {fillot.name} est déjà dans une autre famille",
                ),
            )
        else:
            # Check the family does not have the maximal amount of fillots
            family = families[sg_request.family_token]
            if family.nb_fillots >= max_nb_fillots:
                await manager.send_to(
                    family_token=sg_request.family_token,
                    message=SGResponseMessage(
                        command=Command.sg_failure,
                        fillot_id=sg_request.fillot_id,
                        message="Vous avez déjà suffisamment de fillots",
                    ),
                )
            elif (
                fillot.floor != ADOMA
                and family.nb_fillots_comparat >= max_nb_fillots_comparat
            ):
                await manager.send_to(
                    family_token=sg_request.family_token,
                    message=SGResponseMessage(
                        command=Command.sg_failure,
                        fillot_id=sg_request.fillot_id,
                        fillot_name=fillots[sg_request.fillot_id].fillot_name,
                        message=f"Vous ne pouvez pas prendre plus de {max_nb_fillots_comparat} à Comparat",
                    ),
                )
            # If there are some fillots from this floor (`fillot.floor in family.nb_fillots_by_floors`) and there are to much fillots
            elif (
                fillot.floor in family.nb_fillots_by_floors
                and family.nb_fillots_by_floors[fillot.floor]
                >= max_nb_fillots_by_floors[fillot.floor]
            ):
                await manager.send_to(
                    family_token=sg_request.family_token,
                    message=SGResponseMessage(
                        command=Command.sg_failure,
                        fillot_id=sg_request.fillot_id,
                        fillot_name=fillots[sg_request.fillot_id].fillot_name,
                        message=f"Vous ne pouvez pas prendre plus de {max_nb_fillots_by_floors[fillot.floor]} à l'étage {fillot.floor}",
                    ),
                )
            else:
                # Sg the fillot
                fillot.sged = True
                fillot.family_token = sg_request.family_token
                family.fillot_ids.append(fillot)
                family.nb_fillots += 1
                # If there is currently no fillot from this floor, we can instantiate the variable
                if fillot.floor not in family.nb_fillots_by_floors:
                    family.nb_fillots_by_floors[fillot.floor] = 0
                family.nb_fillots_by_floors[fillot.floor] += 1
                if fillot.floor != ADOMA:
                    family.nb_fillots_comparat += 1

                await manager.send_to(
                    family_token=sg_request.family_token,
                    message=SGResponseMessage(
                        command=Command.sg_success,
                        fillot_id=sg_request.fillot_id,
                        fillot_name=fillots[sg_request.fillot_id].fillot_name,
                        nb_fillots=family.nb_fillots,
                        nb_fillots_comparat=family.nb_fillots_comparat,
                        nb_fillots_by_floors=family.nb_fillots_by_floors,
                    ),
                )
                await manager.send_to_everyone_but(
                    excluded_family_token=sg_request.family_token,
                    message=SGResponseMessage(
                        command=Command.sg_done,
                        fillot_id=sg_request.fillot_id,
                    ),
                )
        print(sg_request)
        #    sg_queue.task_done()


@router.get("/startworker")
async def startworker():  # background_tasks: BackgroundTasks):
    if module_status.locked:
        return "Exiting, the module is locked"
    asyncio.create_task(worker())
    return "ok"


@router.get("/results")
async def results():  # background_tasks: BackgroundTasks):
    return families


@router.websocket("/ws/{family_token}")
async def websocket_endpoint(
    family_token: str,
    websocket: WebSocket,
    # user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.family)),
):

    await manager.connect(websocket=websocket, family_token=family_token)

    if family_token not in families:
        await manager.send_to(
            family_token=family_token, message=Message(command=Command.invalid_token)
        )
        manager.disconnect(family_token=family_token)
        return
    # data = await websocket.receive_json()

    print("New connection", module_status.status)

    if module_status.status == Status.sg:
        print("SG is already started")
        family = families[family_token]
        await manager.send_to(
            family_token=family_token,
            message=StartMessage(
                command=Command.start,
                fillots=remove_family_token(fillots_by_floor),
                family_fillots_ids=[
                    fillot.fillot_id for fillot in family.fillot_ids
                ],  # At the beginning all families have no fillots
                nb_fillots=family.nb_fillots,
                max_nb_fillots=max_nb_fillots,
                nb_fillots_comparat=family.nb_fillots_comparat,
                max_nb_fillots_comparat=max_nb_fillots_comparat,
                nb_fillots_by_floors=family.nb_fillots_by_floors,
                max_nb_fillots_by_floors=max_nb_fillots_by_floors,
                family_name=family.name,
            ),
        )
    elif module_status.status == Status.countdown:
        family = families[family_token]
        await manager.send_to(
            family_token=family_token,
            message=CountdownMessage(
                command=Command.countdown,
                countdown=str(startdatetime.strftime("%H:%M")),
                family_name=family.name,
            ),
        )

    try:
        while True:
            data = await websocket.receive_json()
            if "command" in data and data["command"] == "sg" and "fillot_id" in data:
                sg_request = SGRequest(
                    family_token=family_token, fillot_id=data["fillot_id"]
                )
                now = datetime.now()
                await sg_queue.put(sg_request)
                with open("log.txt", "a") as f:
                    f.write(f"{now}: {family_token} - {data['fillot_id']}\n")

            else:
                pass
                # TODO: Send error

    except WebSocketDisconnect:
        manager.disconnect(family_token=family_token)
        # await manager.broadcast("Client #{client_id} left the chat")
        print("Got a DISCONNECT failure")
        pass
