import asyncio
import logging
from enum import Enum

from broadcaster import Broadcast
from fastapi import WebSocket
from pydantic import BaseModel

from app.core.config import Settings


class HyperionWebsocketsRoom(str, Enum):
    CDR = "5a816d32-8b5d-4c44-8a8d-18fd830ec5a8"


hyperion_error_logger = logging.getLogger("hyperion.error")


class MessageToRoomModel(BaseModel):
    message: str
    room_id: HyperionWebsocketsRoom


class WebsocketConnectionManager:
    def __init__(self, settings: Settings):
        """
        Initialize the ConnectionManager.

        The ConnectionManager is responsible for multiple rooms. A room is a set of connected websocket over which messages can be broadcasted.

        When using multiple Hyperion workers, a websocket may be open with any worker.
        To be able to broadcast messages to all connected websocket, we need to send it to all open websocket from all workers.

        To do this, the class use a broadcaster.

        When a message must be send to a room:
         - the worker send the message to its connected websocket
         - the worker transmit the message over broadcaster
         - all workers will receive the message from the broadcaster and send it to its connected websocket


        You must configure a Redis server to use this feature.
        Without Redis, a memory broadcaster is used, which should not work with multiple workers.
        """
        self.broadcaster: Broadcast = (
            Broadcast(settings.REDIS_URL)
            if settings.REDIS_HOST
            else Broadcast("memory://")
        )

        # For each Room, we store the set of connected websockets
        self.connections: dict[
            HyperionWebsocketsRoom,
            set[WebSocket],
        ] = {}

        self.listening_tasks: dict[HyperionWebsocketsRoom, asyncio.Task] = {}

    async def connect_broadcaster(self):
        await self.broadcaster.connect()

    async def disconnect_broadcaster(self):
        await self.broadcaster.disconnect()

    async def add_connection_to_room(
        self,
        room_id: HyperionWebsocketsRoom,
        ws_connection: WebSocket,
    ) -> None:
        """
        To add a connection to a room:
          - store the websocket connection in the room set
          - listen to the room over the broadcaster if it wasn't already done to
            see incoming messages from other workers that need to be send over websocket
        """
        if room_id not in self.connections:
            self.connections[room_id] = set({ws_connection})

            # This worker wasn't listening to this room over the broadcaster yet because it didn't had any open websocket connection for this room.
            # We will start to listen to the room over the broadcaster.
            subscribe_n_listen_task = asyncio.create_task(
                self._subscribe_and_listen_to_channel(room_id=room_id),
            )

            self.listening_tasks[room_id] = subscribe_n_listen_task

            # To prevent keeping references to finished tasks forever,
            # make each task remove its own reference from the set after
            # completion:
            # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task

            subscribe_n_listen_task.add_done_callback(
                lambda task: self.listening_tasks.pop(room_id),
            )

            print(subscribe_n_listen_task)

        else:
            self.connections[room_id].add(ws_connection)

    async def _consume_events(self, message: str, room_id: HyperionWebsocketsRoom):
        room_connections: set[WebSocket] = self.connections.get(room_id, set())
        to_delete = []
        if len(room_connections) == 0:
            return

        for connection in room_connections:
            if not await self._send_message_to_ws_connection(
                message=message,
                ws_connection=connection,
            ):
                to_delete.append(connection)

        for connection in to_delete:
            for k in self.connections:
                if connection in self.connections[k]:
                    self.connections[k].remove(connection)

    async def remove_connection_from_room(
        self,
        connection: WebSocket,
        room_id: HyperionWebsocketsRoom,
    ):
        if connection in self.connections[room_id]:
            self.connections[room_id].remove(connection)
        # If there is no more connection in the room, we can stop listening to the room over the broadcaster
        if len(self.connections[room_id]) == 0:
            del self.connections[room_id]
            # TODO

    async def _subscribe_and_listen_to_channel(self, room_id: str):
        async with self.broadcaster.subscribe(channel=room_id) as subscriber:
            async for event in subscriber:
                message = MessageToRoomModel.model_validate_json(event.message)

                await self._consume_events(
                    message=message.message,
                    room_id=message.room_id,
                )


    def _unsubscribe_channel(self, room_id: str):
        if room_id in self.listening_tasks:
            # By cancelling the task, asyncio will raise a CancelledError in the task
            # forcing the broadcaster to stop listening to the room
            # The finally block of `broadcaster.subscribe()` will ensure that the channel is unsubscribed from Redis/local memory
            self.listening_tasks[room_id].cancel()
            # del self.listening_tasks # Should be done by the callback

    async def send_message_to_room(self, message: str, room_id: HyperionWebsocketsRoom):
        room_connections: set[WebSocket] = self.connections.get(room_id, set())

        if len(room_connections) == 0:
            return

        await self.broadcaster.publish(
            channel=room_id,
            message=MessageToRoomModel(
                message=message,
                room_id=room_id,
            ).model_dump_json(),
        )

    async def _send_message_to_ws_connection(
        self,
        message: str,
        ws_connection: WebSocket,
    ) -> bool:
        try:
            await ws_connection.send_text(message)
        except RuntimeError:
            return False

        except Exception:
            hyperion_error_logger.exception("Error while sending websocket message")
            return False
        else:
            return True
