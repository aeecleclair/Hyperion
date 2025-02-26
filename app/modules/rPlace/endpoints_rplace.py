import logging
import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.core_endpoints import models_core
from app.dependencies import (
    get_db,
    get_settings,
    get_unsafe_db,
    get_websocket_connection_manager,
    is_user,
    is_user_a_member,
)
from app.modules.rPlace import coredata_rplace, cruds_rplace, models_rplace, schemas_rplace
from app.types.module import Module
from app.types.websocket import HyperionWebsocketsRoom, WebsocketConnectionManager
from app.utils.tools import get_core_data

module = Module(
    root="rplace",
    tag="rplace",
)

hyperion_error_logger = logging.getLogger("hyperion_error_logger")


@module.router.get(
    "/rplace/pixels",
    response_model=list[schemas_rplace.Pixel],
    status_code=200,
)
async def get_pixels(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_rplace.get_pixels(db=db)


@module.router.post(
    "/rplace/pixels",
    response_model=schemas_rplace.Pixel,
    status_code=201,
)
async def create_pixel(
    pixel: schemas_rplace.Pixel,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
    ws_manager: WebsocketConnectionManager = Depends(get_websocket_connection_manager),
):
    pixel_id = uuid.uuid4()

    db_item = models_rplace.Pixel(
        id=pixel_id,
        date=datetime.now(tz=UTC),
        user_id=user.id,
        x=pixel.x,
        y=pixel.y,
        color=pixel.color,
    )
    try:
        res = await cruds_rplace.create_pixel(
            rplace_pixel=db_item,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    try:
        await ws_manager.send_message_to_room(
            message=schemas_rplace.NewPixelWSMessageModel(
                data=schemas_rplace.Pixel(
                    x=pixel.x,
                    y=pixel.y,
                    color=pixel.color,
                ),
            ),
            room_id=HyperionWebsocketsRoom.Rplace,
        )
    except Exception:
        hyperion_error_logger.exception(
            f"Error while sending a message to the room {HyperionWebsocketsRoom.CDR}",
        )
    return res

@module.router.get(
    "/rplace/information",
    response_model=coredata_rplace.gridInformation,
    status_code=200,
)
async def get_grid_information(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get grid information
    """
    return await get_core_data(coredata_rplace.gridInformation, db)


@module.router.websocket("/rplace/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ws_manager: WebsocketConnectionManager = Depends(get_websocket_connection_manager),
    db: AsyncSession = Depends(get_unsafe_db),
    settings: Settings = Depends(get_settings),
):
    await ws_manager.manage_websocket(
        websocket=websocket,
        settings=settings,
        room=HyperionWebsocketsRoom.Rplace,
        db=db,
    )
