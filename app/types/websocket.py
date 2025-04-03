import asyncio
import logging
import os
from enum import Enum
from typing import Any, Literal

from broadcaster import Broadcast
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.config import Settings
from app.types.scopes_type import ScopeType
from app.utils.auth import auth_utils


class HyperionWebsocketsRoom(str, Enum):
    Purchases = "5a816d32-8b5d-4c44-8a8d-18fd830ec5a8"


hyperion_error_logger = logging.getLogger("hyperion.error")


class WSMessageModel(BaseModel):
    command: str
    data: Any


class ConnectionWSMessageModelStatus(str, Enum):
    connected = "connected"
    invalid = "invalid_token"


class ConnectionWSMessageModelData(BaseModel):
    status: ConnectionWSMessageModelStatus


class ConnectionWSMessageModel(BaseModel):
    command: Literal["WSStatus"] = "WSStatus"
    data: ConnectionWSMessageModelData


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
            if settings.REDIS_URL
            else Broadcast("memory://")
        )

        # For each Room, we store the set of connected websockets
        self.connections: dict[
            HyperionWebsocketsRoom,
            set[WebSocket],
        ] = {}

        # We keep a reference to the listening tasks for each room
        # to be able to stop listening to a room when there is no more connection
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
                lambda task: self._remove_task_from_listening_tasks_callback(room_id),
            )

        else:
            self.connections[room_id].add(ws_connection)

    def _remove_task_from_listening_tasks_callback(
        self,
        room_id: HyperionWebsocketsRoom,
    ):
        """
        Asyncio task callback to remove the task from the listening_tasks dict
        The method is called after the listening task is done or cancelled
        """
        self.listening_tasks.pop(room_id, None)
        self.connections.pop(room_id, None)
        hyperion_error_logger.info(
            f"Websocket: unsubscribed broadcaster from channel {room_id} for worker {os.getpid()}",
        )

    async def _consume_events_from_broadcaster(
        self,
        message_str: str,
        room_id: HyperionWebsocketsRoom,
    ):
        """
        Handle an incoming message from the broadcaster. Send the message to all connected websocket in the room.
        """
        room_connections: set[WebSocket] = self.connections.get(room_id, set())
        if len(room_connections) == 0:
            # If we don't have any connection in the room, we don't need to keep listening to the room over the broadcaster
            self._unsubscribe_channel(room_id)
            return

        for connection in room_connections:
            if not await self._send_message_to_ws_connection(
                message_str=message_str,
                ws_connection=connection,
            ):
                # If the message couldn't be sent to the connection, we disconnect the websocket connection
                await connection.close(reason="Failed to send message to websocket")

    async def remove_connection_from_room(
        self,
        connection: WebSocket,
        room_id: HyperionWebsocketsRoom,
    ):
        """
        Remove a websocket connection from a room.
        If there is no more connection in the room, we stop listening to the room over the broadcaster
        """
        if connection in self.connections[room_id]:
            self.connections[room_id].remove(connection)

        # If there is no more connection in the room, we can stop listening to the room over the broadcaster
        if len(self.connections[room_id]) == 0:
            self._unsubscribe_channel(room_id)

    async def _subscribe_and_listen_to_channel(self, room_id: HyperionWebsocketsRoom):
        """
        Subscribe to a channel and listen to incoming messages. Incoming messages are sent over open websocket connections.
        """
        async with self.broadcaster.subscribe(channel=room_id) as subscriber:
            hyperion_error_logger.info(
                f"Websocket: subscribed broadcaster to channel {room_id} for worker {os.getpid()}",
            )

            async for event in subscriber:  # type: ignore # Should be fixed by https://github.com/encode/broadcaster/issues/136
                await self._consume_events_from_broadcaster(
                    message_str=event.message,  # type: ignore # Should be fixed by https://github.com/encode/broadcaster/issues/136
                    room_id=room_id,
                )

        hyperion_error_logger.info(
            f"Websocket: Finished listening to channel {room_id} for worker {os.getpid()}",
        )

    def _unsubscribe_channel(self, room_id: HyperionWebsocketsRoom):
        if room_id in self.listening_tasks:
            # By cancelling the task, asyncio will raise a CancelledError in the task
            # forcing the broadcaster to stop listening to the room
            # The finally block of `broadcaster.subscribe()` will ensure that the channel is unsubscribed from Redis/local memory
            self.listening_tasks[room_id].cancel()
            # del self.listening_tasks # Should be done by the callback

    async def send_message_to_room(
        self,
        message: WSMessageModel,
        room_id: HyperionWebsocketsRoom,
    ):
        # We need to send the message over the broadcaster even if there is no connection in the room for this worker
        # Because other workers may have open websocket connections for this room

        await self.broadcaster.publish(
            channel=room_id,
            message=message.model_dump_json(),
        )

    async def _send_message_to_ws_connection(
        self,
        message_str: str,
        ws_connection: WebSocket,
    ) -> bool:
        try:
            await ws_connection.send_text(message_str)
        except RuntimeError:
            return False
        except Exception:
            hyperion_error_logger.exception("Error while sending websocket message")
            return False
        return True

    async def manage_websocket(
        self,
        websocket: WebSocket,
        settings: Settings,
        room: HyperionWebsocketsRoom,
        db: AsyncSession,
    ):
        """
        This function is used to manage the websocket connection.

        It will create an infinite loop that will wait for messages from the websocket.
        The loop will be broken when the websocket is disconnected.

        The databse is closed manually in this method, so you need to use the dependency `get_unsafe_db` in the FastAPI endpoint.

        NOTE:
        - you should not call methods after this call, as it will be unreachable until the websocket is disconnected
        - you should never use `get_db` in the websocket endpoint, as the connection will never be closed  until the websocket is disconnected
        If you use `get_db` in the websocket endpoint, you will have a lot of open connections to the database at the same time, which will led to a Postgresql error.
        """

        await websocket.accept()

        try:
            token_message = await websocket.receive_json()
            token = token_message.get("token", None)

            token_data = auth_utils.get_token_data(
                settings=settings,
                token=token,
                request_id="websocket",
            )

            user = await auth_utils.get_user_from_token_with_scopes(
                scopes=[[ScopeType.API]],
                db=db,
                token_data=token_data,
            )
        except Exception:
            await websocket.send_text(
                ConnectionWSMessageModel(
                    data=ConnectionWSMessageModelData(
                        status=ConnectionWSMessageModelStatus.invalid,
                    ),
                ).model_dump_json(),
            )
            await websocket.close()
            return
        finally:
            await db.close()

        hyperion_error_logger.debug(
            f"{room}: New websocket connection from {user.id} on worker {os.getpid()}",
        )

        await websocket.send_text(
            ConnectionWSMessageModel(
                data=ConnectionWSMessageModelData(
                    status=ConnectionWSMessageModelStatus.connected,
                ),
            ).model_dump_json(),
        )

        # Add the user to the connection stack
        await self.add_connection_to_room(
            room_id=room,
            ws_connection=websocket,
        )

        try:
            while True:
                # TODO: we could use received messages from the websocket
                await websocket.receive_json()
        except WebSocketDisconnect:
            await self.remove_connection_from_room(
                room_id=room,
                connection=websocket,
            )
        except Exception:
            await self.remove_connection_from_room(
                room_id=room,
                connection=websocket,
            )
            raise
