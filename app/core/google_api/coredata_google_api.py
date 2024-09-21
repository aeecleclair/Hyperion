from datetime import datetime

from app.types.core_data import BaseCoreData


class GoogleAPICredentials(BaseCoreData):
    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]
    expiry: datetime
