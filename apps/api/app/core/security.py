from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


class TokenValidationError(Exception):
    """
    JWT校验失败。
    """

    pass


def hash_password(
    plain_password: str,
) -> str:
    """
    对用户明文密码进行不可逆哈希。
    """

    if not plain_password:
        raise ValueError(
            "Password cannot be empty."
        )

    return password_hash.hash(plain_password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    校验用户输入的密码是否匹配数据库哈希。
    """

    if not plain_password or not hashed_password:
        return False

    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(
    *,
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    创建平台访问令牌。

    subject通常保存用户ID。
    """

    if not subject:
        raise ValueError(
            "Token subject cannot be empty."
        )

    now = datetime.now(timezone.utc)

    expires_at = now + timedelta(
        minutes=settings.access_token_expire_minutes,
    )

    payload: dict[str, Any] = dict(
        extra_claims or {}
    )

    # 受保护字段最后写入，防止被额外字段覆盖。
    payload.update(
        {
            "sub": subject,
            "iat": now,
            "exp": expires_at,
            "type": "access",
        }
    )

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(
    token: str,
) -> dict[str, Any]:
    """
    校验并解析平台访问令牌。
    """

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[
                settings.jwt_algorithm,
            ],
        )

    except InvalidTokenError as exc:
        raise TokenValidationError(
            "The access token is invalid or expired."
        ) from exc

    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject:
        raise TokenValidationError(
            "The access token has no valid subject."
        )

    if payload.get("type") != "access":
        raise TokenValidationError(
            "The token is not an access token."
        )

    return payload