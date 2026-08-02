from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class RegisterRequest(BaseModel):
    """
    用户注册请求。
    """

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    display_name: str | None = Field(
        default=None,
        max_length=100,
    )

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()

        if not normalized_value:
            return None

        return normalized_value


class LoginRequest(BaseModel):
    """
    用户登录请求。
    """

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


class UserResponse(BaseModel):
    """
    返回给前端的安全用户信息。

    不包含密码哈希。
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    email: EmailStr
    display_name: str | None

    role: str
    is_active: bool
    is_verified: bool

    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """
    登录成功后的令牌响应。
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int

    user: UserResponse