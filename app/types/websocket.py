import asyncio
import logging
from enum import Enum

from broadcaster import Broadcast  # type: ignore
from fastapi import WebSocket
from pydantic import BaseModel

from app.dependencies import get_settings


class HyperionWebsocketsRoom(str, Enum):
    CDR = "5a816d32-8b5d-4c44-8a8d-18fd830ec5a8"


hyperion_error_logger = logging.getLogger("hyperion.error")


class MessageToRoomModel(BaseModel):
    message: str
    room_id: HyperionWebsocketsRoom


class ConnectionManager:
    settings = get_settings()
    broadcaster = (
        Broadcast(settings.REDIS_HOST)
        if settings.REDIS_HOST
        else Broadcast("memory://")
    )

    def __init__(self):
        self.connections: dict[
            HyperionWebsocketsRoom,
            set[WebSocket],
        ] = {}  # The Room and the set of users connected

    async def connect_broadcaster(self):
        await self.broadcaster.connect()

    async def disconnect_broadcaster(self):
        await self.broadcaster.disconnect()

    async def add_connection_to_room(
        self,
        room_id: HyperionWebsocketsRoom,
        ws_connection: WebSocket,
    ) -> bool:
        if room_id not in self.connections:
            self.connections[room_id] = set({ws_connection})

            subscribe_n_listen_task = asyncio.create_task(
                self._subscribe_and_listen_to_channel(room_id=room_id),
            )
            wait_for_subscribe_task = asyncio.create_task(asyncio.sleep(1))

            await asyncio.wait(
                [subscribe_n_listen_task, wait_for_subscribe_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
        else:
            self.connections[room_id].add(ws_connection)

        return True

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

    async def remove_connection_from_room(self, connection: WebSocket, room_id: HyperionWebsocketsRoom):
        if connection in self.connections[room_id]:
            self.connections[room_id].remove(connection)

    async def _subscribe_and_listen_to_channel(self, room_id: str):
        async with self.broadcaster.subscribe(channel=room_id) as subscriber:
            async for event in subscriber:
                message = MessageToRoomModel.model_validate_json(event.message)

                await self._consume_events(
                    message=message.message,
                    room_id=message.room_id,
                )

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
            return True
        except RuntimeError:
            return False

        except Exception as e:
            hyperion_error_logger.error(f"Error while sending websocket message : {e}")
            return False


ws_manager = ConnectionManager()
