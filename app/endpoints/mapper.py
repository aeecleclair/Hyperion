from fastapi import (
    APIRouter,
    Header,
    Depends,
    HTTPException,
)

from app.core.config import Settings
from app.dependencies import (
    get_settings,
)
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/users_mapper",
    status_code=200,
    tags=[Tags.core],
)
async def get_users_mapper(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
):
    if authorization != f"Bearer {settings.SYNAPSE_USER_MAPPER_SECRET}":
        raise HTTPException(status_code=401, detail="Invalid token")

    return {
        "userMapping": {
            "@user1:127.0.0.1": {
                "displayName": "MyUser1",
                "rooms": [
                    "!nEXBNJxjiTbHcJJitj:127.0.0.1",
                    "!hNxsHcIuWVhUAHvYUw:127.0.0.1",
                    "!SzJapSTLoRWDUiuNfH:127.0.0.1",
                    "!krLbAAMPEBhOpuHKEM:127.0.0.1",
                ],
            },
            "@user10:127.0.0.1": {
                "displayName": "MyUser10",
                "rooms": [
                    "!nEXBNJxjiTbHcJJitj:127.0.0.1",
                    "!hNxsHcIuWVhUAHvYUw:127.0.0.1",
                    "!SzJapSTLoRWDUiuNfH:127.0.0.1",
                    "!krLbAAMPEBhOpuHKEM:127.0.0.1",
                ],
            },
        },
        "roomModerators": {
            "!nEXBNJxjiTbHcJJitj:127.0.0.1": "@armand:127.0.0.1",
            "!hNxsHcIuWVhUAHvYUw:127.0.0.1": "@armand:127.0.0.1",
            "!SzJapSTLoRWDUiuNfH:127.0.0.1": "@armand:127.0.0.1",
            "!krLbAAMPEBhOpuHKEM:127.0.0.1": "@armand:127.0.0.1",
        },
    }
