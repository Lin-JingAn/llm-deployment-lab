import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


API_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = API_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True,
)


def get_env_int(
    name: str,
    default: int,
) -> int:
    """
    读取整数环境变量。
    """

    raw_value = os.getenv(name)

    if raw_value is None or not raw_value.strip():
        return default

    try:
        return int(raw_value.strip())
    except ValueError as exc:
        raise RuntimeError(
            f"Environment variable '{name}' "
            f"must be an integer, got: {raw_value!r}"
        ) from exc


@dataclass(frozen=True)
class Settings:
    """
    平台统一配置。
    """

    app_name: str
    app_version: str
    environment: str

    litellm_base_url: str
    litellm_api_key: str
    default_model_id: str

    max_conversation_messages: int
    max_conversation_characters: int
    request_timeout_seconds: int

    web_origin: str

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int


def create_settings() -> Settings:
    settings = Settings(
        app_name=os.getenv(
            "APP_NAME",
            "Unified LLM Platform API",
        ).strip(),

        app_version=os.getenv(
            "APP_VERSION",
            "0.5.0",
        ).strip(),

        environment=os.getenv(
            "APP_ENV",
            "development",
        ).strip(),

        litellm_base_url=os.getenv(
            "LITELLM_BASE_URL",
            "http://127.0.0.1:4000/v1",
        ).strip().rstrip("/"),

        litellm_api_key=os.getenv(
            "LITELLM_API_KEY",
            "",
        ).strip(),

        default_model_id=os.getenv(
            "DEFAULT_MODEL_ID",
            "qwen-plus",
        ).strip(),

        max_conversation_messages=get_env_int(
            "MAX_CONVERSATION_MESSAGES",
            20,
        ),

        max_conversation_characters=get_env_int(
            "MAX_CONVERSATION_CHARACTERS",
            60000,
        ),

        request_timeout_seconds=get_env_int(
            "REQUEST_TIMEOUT_SECONDS",
            120,
        ),

        web_origin=os.getenv(
            "WEB_ORIGIN",
            "http://127.0.0.1:5500",
        ).strip().rstrip("/"),

        db_host=os.getenv(
            "DB_HOST",
            "127.0.0.1",
        ).strip(),

        db_port=get_env_int(
            "DB_PORT",
            5433,
        ),

        db_name=os.getenv(
            "DB_NAME",
            "unified_llm",
        ).strip(),

        db_user=os.getenv(
            "DB_USER",
            "litellm",
        ).strip(),

        db_password=os.getenv(
            "DB_PASSWORD",
            "",
        ).strip(),

        jwt_secret_key=os.getenv(
            "JWT_SECRET_KEY",
            "",
        ).strip(),

        jwt_algorithm=os.getenv(
            "JWT_ALGORITHM",
            "HS256",
        ).strip(),

        access_token_expire_minutes=get_env_int(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            60,
        ),
    )

    if not settings.litellm_api_key:
        raise RuntimeError(
            "LITELLM_API_KEY is missing from "
            f"{ENV_FILE}"
        )

    if not settings.db_password:
        raise RuntimeError(
            "DB_PASSWORD is missing from "
            f"{ENV_FILE}"
        )

    if not settings.jwt_secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY is missing from "
            f"{ENV_FILE}"
        )

    if settings.jwt_algorithm != "HS256":
        raise RuntimeError(
            "JWT_ALGORITHM must currently be HS256."
        )

    return settings


settings = create_settings()