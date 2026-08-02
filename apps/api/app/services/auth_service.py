from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest


class EmailAlreadyRegisteredError(Exception):
    """
    邮箱已经被注册。
    """

    pass


def normalize_email(
    email: str,
) -> str:
    """
    统一邮箱格式。
    """

    return email.strip().lower()


def get_user_by_email(
    database_session: Session,
    email: str,
) -> User | None:
    """
    根据邮箱查找用户。
    """

    normalized_email = normalize_email(email)

    statement = select(User).where(
        User.email == normalized_email
    )

    return database_session.scalar(statement)


def create_user(
    *,
    database_session: Session,
    request: RegisterRequest,
) -> User:
    """
    创建新用户。
    """

    normalized_email = normalize_email(
        str(request.email)
    )

    existing_user = get_user_by_email(
        database_session,
        normalized_email,
    )

    if existing_user is not None:
        raise EmailAlreadyRegisteredError(
            "This email address is already registered."
        )

    user = User(
        email=normalized_email,
        hashed_password=hash_password(
            request.password
        ),
        display_name=request.display_name,
        role="user",
        is_active=True,
        is_verified=False,
    )

    database_session.add(user)

    try:
        database_session.commit()

    except IntegrityError as exc:
        database_session.rollback()

        raise EmailAlreadyRegisteredError(
            "This email address is already registered."
        ) from exc

    database_session.refresh(user)

    return user


def authenticate_user(
    *,
    database_session: Session,
    email: str,
    password: str,
) -> User | None:
    """
    校验邮箱和密码。
    """

    user = get_user_by_email(
        database_session,
        email,
    )

    if user is None:
        return None

    if not verify_password(
        password,
        user.hashed_password,
    ):
        return None

    return user