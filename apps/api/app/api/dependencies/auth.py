from typing import Annotated
from uuid import UUID

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.core.security import (
    TokenValidationError,
    decode_access_token,
)
from app.db.session import get_db
from app.models.user import User


bearer_scheme = HTTPBearer(
    auto_error=False,
)


def authentication_error() -> HTTPException:
    """
    创建统一的401错误。
    """

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "message": (
                "A valid access token is required."
            ),
            "error_type": (
                "authentication_required"
            ),
        },
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> User:
    """
    从Bearer Token中读取当前用户。
    """

    if credentials is None:
        raise authentication_error()

    try:
        payload = decode_access_token(
            credentials.credentials
        )

        user_id = UUID(
            payload["sub"]
        )

    except (
        TokenValidationError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise authentication_error() from exc

    user = database_session.get(
        User,
        user_id,
    )

    if user is None:
        raise authentication_error()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": (
                    "This user account is disabled."
                ),
                "error_type": "user_disabled",
            },
        )

    return user