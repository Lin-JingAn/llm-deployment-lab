import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.model_calls import router as model_calls_router
from app.core.config import settings
from app.core.model_registry import get_enabled_models


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Unified multi-provider LLM service platform."
    ),
)


# ========================================
# CORS配置
# ========================================

allowed_origins = [
    settings.web_origin,
]

# 同时兼容127.0.0.1和localhost访问网页。
if "127.0.0.1" in settings.web_origin:
    allowed_origins.append(
        settings.web_origin.replace(
            "127.0.0.1",
            "localhost",
        )
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# 注册API路由
# ========================================


app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(model_calls_router)
app.include_router(chat_router)


# ========================================
# 基础接口
# ========================================

@app.get("/")
async def root() -> dict:
    """
    返回平台基础信息。
    """

    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "readiness": "/health/readiness",
        "models": "/models",
        "model_calls": "/model-calls",
        "model_call_summary": "/model-calls/summary",
        "conversations": "/conversations",
        "chat": "/chat",
        "chat_stream": "/chat/stream",
    }


@app.get("/health")
async def health() -> dict:
    """
    FastAPI存活检查。

    这里只检查应用本身是否正常运行，
    不检查LiteLLM和上游模型。
    """

    enabled_models = get_enabled_models()

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "default_model": settings.default_model_id,
        "enabled_model_count": len(enabled_models),
        "litellm_gateway": (
            settings.litellm_base_url
        ),
        "api_key_loaded": bool(
            settings.litellm_api_key
        ),
    }


def get_litellm_readiness_url() -> str:
    """
    根据LiteLLM的OpenAI兼容地址，
    生成LiteLLM健康检查地址。
    """

    gateway_root = settings.litellm_base_url

    if gateway_root.endswith("/v1"):
        gateway_root = gateway_root[:-3]

    return (
        f"{gateway_root.rstrip('/')}"
        "/health/readiness"
    )


@app.get("/health/readiness")
async def readiness() -> dict:
    """
    检查FastAPI是否能够连接LiteLLM。
    """

    readiness_url = get_litellm_readiness_url()

    try:
        async with httpx.AsyncClient(
            timeout=5.0,
            trust_env=False,
        ) as client:
            response = await client.get(
                readiness_url
            )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": (
                    "FastAPI could not connect "
                    "to LiteLLM."
                ),
                "error_type": (
                    "litellm_connection_error"
                ),
            },
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=503,
            detail={
                "message": (
                    "LiteLLM is not ready."
                ),
                "error_type": (
                    "litellm_not_ready"
                ),
                "upstream_status_code": (
                    response.status_code
                ),
            },
        )

    try:
        upstream_data = response.json()
    except ValueError:
        upstream_data = {
            "raw_response": response.text[:500],
        }

    return {
        "status": "ready",
        "fastapi": "ready",
        "litellm": "ready",
        "litellm_url": readiness_url,
        "litellm_response": upstream_data,
    }