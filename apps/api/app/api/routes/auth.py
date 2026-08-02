from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import (
    get_current_user,
)
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    authenticate_user,
    create_user,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> User:
    """
    注册新用户。
    """

    try:
        return create_user(
            database_session=database_session,
            request=request,
        )

    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "error_type": (
                    "email_already_registered"
                ),
            },
        ) from exc


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> TokenResponse:
    """
    用户登录并签发JWT。
    """

    user = authenticate_user(
        database_session=database_session,
        email=str(request.email),
        password=request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": (
                    "The email address or password "
                    "is incorrect."
                ),
                "error_type": (
                    "invalid_login_credentials"
                ),
            },
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

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

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "role": user.role,
            "email": user.email,
        },
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=(
            settings.access_token_expire_minutes
            * 60
        ),
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def read_current_user(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> User:
    """
    返回当前登录用户。
    """

    return current_user