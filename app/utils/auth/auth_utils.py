import logging

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError
from pydantic import ValidationError

from app.core.auth import schemas_auth
from app.core.utils import security
from app.core.utils.config import Settings

hyperion_access_logger = logging.getLogger("hyperion.access")


def get_token_data(
    settings: Settings,
    token: str,
    request_id: str,
) -> schemas_auth.TokenData:
    """
    Dependency that returns the token payload data
    """
    try:
        payload = jwt.decode(
            token,
            settings.ACCESS_TOKEN_SECRET_KEY,
            algorithms=[security.jwt_algorithm],
        )
        token_data = schemas_auth.TokenData(**payload)
        hyperion_access_logger.info(
            f"Get_token_data: Decoded a token for user {token_data.sub} ({request_id})",
        )
    except (InvalidTokenError, ValidationError):
        hyperion_access_logger.exception(
            f"Get_token_data: Failed to decode a token ({request_id})",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        ) from None
    except ExpiredSignatureError:
        hyperion_access_logger.exception(
            f"Get_token_data: Token has expired ({request_id})",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token has expired",
        ) from None
    except DecodeError:
        hyperion_access_logger.exception(
            f"Get_token_data: Failed to decode a token ({request_id})",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        ) from None

    return token_data
