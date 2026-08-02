import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings
from app.core.model_registry import ModelConfig
from app.schemas.chat import ChatRequest, ChatResponse, TokenUsage


class ModelGatewayError(Exception):
    """
    模型网关统一异常。

    路由层只处理标准化后的错误，
    不直接依赖不同供应商的原始错误格式。
    """

    def __init__(
        self,
        *,
        status_code: int,
        error_type: str,
        message: str,
        upstream_status_code: int | None = None,
        upstream_body: str | None = None,
    ) -> None:
        super().__init__(message)

        self.status_code = status_code
        self.error_type = error_type
        self.message = message
        self.upstream_status_code = upstream_status_code
        self.upstream_body = upstream_body


def create_request_id() -> str:
    """
    生成平台调用编号。
    """

    return f"req_{uuid.uuid4().hex}"


def serialize_messages(
    request: ChatRequest,
) -> list[dict[str, str]]:
    """
    将聊天消息转换成上游接口需要的字典格式。
    """

    return [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in request.messages
    ]


def resolve_max_output_tokens(
    request: ChatRequest,
    model_config: ModelConfig,
) -> int:
    """
    计算实际使用的最大输出Token数。

    优先级：
    1. 新接口字段 max_output_tokens
    2. 旧网页字段 max_tokens
    3. 模型默认值
    """

    requested_value = request.max_output_tokens

    if requested_value is None:
        requested_value = request.max_tokens

    if requested_value is None:
        requested_value = (
            model_config.default_max_output_tokens
        )

    return min(
        requested_value,
        model_config.max_output_tokens,
    )


def resolve_temperature(
    request: ChatRequest,
    model_config: ModelConfig,
) -> float:
    """
    计算普通聊天模式的温度参数。
    """

    if request.temperature is not None:
        return request.temperature

    return model_config.default_temperature


def build_upstream_payload(
    *,
    request: ChatRequest,
    model_config: ModelConfig,
    stream: bool,
) -> dict[str, Any]:
    """
    把平台统一请求转换为LiteLLM请求。

    不同模型供应商的参数差异统一在这里处理。
    """

    payload: dict[str, Any] = {
        "model": model_config.upstream_model,
        "messages": serialize_messages(request),
        "stream": stream,
        "max_tokens": resolve_max_output_tokens(
            request,
            model_config,
        ),
    }

    reasoning_enabled = request.mode == "reasoning"

    if (
        reasoning_enabled
        and not model_config.supports_reasoning
    ):
        raise ModelGatewayError(
            status_code=400,
            error_type="reasoning_not_supported",
            message=(
                f"Model '{model_config.public_id}' "
                "does not support reasoning mode."
            ),
        )

    if model_config.provider == "Alibaba Cloud Bailian":
        # Qwen混合思考模型参数。
        payload["enable_thinking"] = reasoning_enabled

        if not reasoning_enabled:
            payload["temperature"] = resolve_temperature(
                request,
                model_config,
            )

    elif model_config.provider == "DeepSeek":
        # DeepSeek V4思考模式参数。
        payload["thinking"] = {
            "type": (
                "enabled"
                if reasoning_enabled
                else "disabled"
            ),
        }

        if reasoning_enabled:
            payload["reasoning_effort"] = "high"
        else:
            payload["temperature"] = resolve_temperature(
                request,
                model_config,
            )

    else:
        # 未来没有专属适配器时使用通用OpenAI参数。
        payload["temperature"] = resolve_temperature(
            request,
            model_config,
        )

    if stream:
        payload["stream_options"] = {
            "include_usage": True,
        }

    return payload


def extract_usage(
    data: dict[str, Any],
) -> TokenUsage:
    """
    从LiteLLM或供应商响应中提取Token明细。
    """

    usage = data.get("usage") or {}

    input_tokens = int(
        usage.get("prompt_tokens")
        or usage.get("input_tokens")
        or 0
    )

    output_tokens = int(
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or 0
    )

    total_tokens = int(
        usage.get("total_tokens")
        or input_tokens + output_tokens
    )

    completion_details = (
        usage.get("completion_tokens_details")
        or usage.get("output_tokens_details")
        or {}
    )

    prompt_details = (
        usage.get("prompt_tokens_details")
        or usage.get("input_tokens_details")
        or {}
    )

    reasoning_tokens = int(
        completion_details.get("reasoning_tokens")
        or usage.get("reasoning_tokens")
        or 0
    )

    cached_tokens = int(
        prompt_details.get("cached_tokens")
        or usage.get("prompt_cache_hit_tokens")
        or usage.get("cached_tokens")
        or 0
    )

    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        reasoning_tokens=reasoning_tokens,
        cached_tokens=cached_tokens,
    )


def usage_to_dict(
    usage: TokenUsage,
) -> dict[str, Any]:
    """
    同时兼容Pydantic v1和v2。
    """

    if hasattr(usage, "model_dump"):
        return usage.model_dump()

    return usage.dict()


def safe_upstream_body(
    response_text: str,
) -> str:
    """
    限制错误正文长度，防止日志过长。
    """

    return response_text[:2000]


def raise_for_upstream_status(
    *,
    status_code: int,
    response_text: str,
) -> None:
    """
    把上游HTTP错误转换成平台统一错误。
    """

    normalized_text = response_text.lower()
    safe_body = safe_upstream_body(response_text)

    if status_code == 400:
        error_type = "upstream_invalid_request"
        message = "The upstream model rejected the request."

    elif status_code == 401:
        error_type = "upstream_authentication_error"
        message = "The upstream model API key is invalid."

    elif (
        status_code == 402
        or (
            "insufficient" in normalized_text
            and "balance" in normalized_text
        )
    ):
        error_type = "upstream_insufficient_balance"
        message = (
            "The upstream model account "
            "has insufficient balance."
        )

    elif status_code == 403:
        error_type = "upstream_permission_error"
        message = (
            "The gateway key is not allowed "
            "to access the requested model."
        )

    elif status_code == 404:
        error_type = "upstream_model_not_found"
        message = (
            "The requested upstream model was not found."
        )

    elif status_code in {408, 504}:
        error_type = "upstream_timeout"
        message = "The upstream model request timed out."

    elif status_code == 429:
        error_type = "upstream_rate_limit"
        message = (
            "The upstream model rate limit was reached."
        )

    elif status_code >= 500:
        error_type = "upstream_unavailable"
        message = (
            "The upstream model service is unavailable."
        )

    else:
        error_type = "upstream_http_error"
        message = (
            "The upstream model returned an HTTP error."
        )

    raise ModelGatewayError(
        status_code=502,
        error_type=error_type,
        message=message,
        upstream_status_code=status_code,
        upstream_body=safe_body,
    )


def build_timeout() -> httpx.Timeout:
    """
    统一HTTP超时配置。
    """

    return httpx.Timeout(
        connect=10.0,
        read=float(settings.request_timeout_seconds),
        write=30.0,
        pool=10.0,
    )


async def create_chat_completion(
    *,
    request: ChatRequest,
    model_config: ModelConfig,
) -> ChatResponse:
    """
    执行非流式模型调用。
    """

    request_id = create_request_id()
    started_at = time.perf_counter()

    chat_url = (
        f"{settings.litellm_base_url}/chat/completions"
    )

    headers = {
        "Authorization": (
            f"Bearer {settings.litellm_api_key}"
        ),
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    payload = build_upstream_payload(
        request=request,
        model_config=model_config,
        stream=False,
    )

    try:
        async with httpx.AsyncClient(
            timeout=build_timeout(),
            trust_env=False,
        ) as client:
            response = await client.post(
                chat_url,
                headers=headers,
                json=payload,
            )

    except httpx.TimeoutException as exc:
        raise ModelGatewayError(
            status_code=504,
            error_type="gateway_timeout",
            message=(
                "The model request exceeded "
                "the configured timeout."
            ),
        ) from exc

    except httpx.RequestError as exc:
        raise ModelGatewayError(
            status_code=502,
            error_type="gateway_connection_error",
            message=(
                "FastAPI could not connect to LiteLLM."
            ),
        ) from exc

    if response.status_code >= 400:
        raise_for_upstream_status(
            status_code=response.status_code,
            response_text=response.text,
        )

    total_latency = round(
        time.perf_counter() - started_at,
        3,
    )

    try:
        data = response.json()

        first_choice = data["choices"][0]
        message = first_choice["message"]

        reply = message.get("content") or ""

        reasoning_content = (
            message.get("reasoning_content")
            or None
        )

        finish_reason = (
            first_choice.get("finish_reason")
            or None
        )

        actual_model = (
            data.get("model")
            or model_config.upstream_model
        )

        usage = extract_usage(data)

    except (
        ValueError,
        KeyError,
        IndexError,
        TypeError,
    ) as exc:
        raise ModelGatewayError(
            status_code=502,
            error_type="unexpected_upstream_response",
            message=(
                "LiteLLM returned an unexpected "
                "response format."
            ),
            upstream_body=safe_upstream_body(
                response.text
            ),
        ) from exc

    return ChatResponse(
        request_id=request_id,
        model_id=model_config.public_id,
        actual_model=actual_model,
        display_name=model_config.display_name,
        provider=model_config.provider,
        reply=reply,
        reasoning_content=reasoning_content,
        finish_reason=finish_reason,
        usage=usage,
        ttft_seconds=None,
        total_latency_seconds=total_latency,
        message_count=len(request.messages),
    )


async def stream_chat_completion(
    *,
    request: ChatRequest,
    model_config: ModelConfig,
) -> AsyncIterator[dict[str, Any]]:
    """
    执行流式模型调用。

    输出平台内部标准事件，
    后续由API路由编码为SSE。
    """

    request_id = create_request_id()
    started_at = time.perf_counter()
    first_token_at: float | None = None

    chat_url = (
        f"{settings.litellm_base_url}/chat/completions"
    )

    headers = {
        "Authorization": (
            f"Bearer {settings.litellm_api_key}"
        ),
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    payload = build_upstream_payload(
        request=request,
        model_config=model_config,
        stream=True,
    )

    actual_model = model_config.upstream_model
    finish_reason: str | None = None
    final_usage = TokenUsage()

    yield {
        "type": "metadata",
        "request_id": request_id,
        "model_id": model_config.public_id,
        "actual_model": actual_model,
        "display_name": model_config.display_name,
        "provider": model_config.provider,
    }

    try:
        async with httpx.AsyncClient(
            timeout=build_timeout(),
            trust_env=False,
        ) as client:
            async with client.stream(
                "POST",
                chat_url,
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    response_bytes = await response.aread()

                    response_text = response_bytes.decode(
                        "utf-8",
                        errors="replace",
                    )

                    raise_for_upstream_status(
                        status_code=response.status_code,
                        response_text=response_text,
                    )

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    if not line.startswith("data:"):
                        continue

                    raw_data = line[5:].strip()

                    if raw_data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(raw_data)
                    except json.JSONDecodeError:
                        continue

                    actual_model = (
                        chunk.get("model")
                        or actual_model
                    )

                    chunk_usage = extract_usage(chunk)

                    if chunk_usage.total_tokens > 0:
                        final_usage = chunk_usage

                    choices = chunk.get("choices") or []

                    if not choices:
                        continue

                    first_choice = choices[0]
                    delta = first_choice.get("delta") or {}

                    reasoning_delta = (
                        delta.get("reasoning_content")
                        or ""
                    )

                    content_delta = (
                        delta.get("content")
                        or ""
                    )

                    chunk_finish_reason = (
                        first_choice.get("finish_reason")
                    )

                    if chunk_finish_reason is not None:
                        finish_reason = chunk_finish_reason

                    if (
                        first_token_at is None
                        and (
                            reasoning_delta
                            or content_delta
                        )
                    ):
                        first_token_at = time.perf_counter()

                    if reasoning_delta:
                        yield {
                            "type": "reasoning_delta",
                            "request_id": request_id,
                            "content": reasoning_delta,
                        }

                    if content_delta:
                        yield {
                            "type": "content_delta",
                            "request_id": request_id,
                            "content": content_delta,
                        }

    except ModelGatewayError:
        raise

    except httpx.TimeoutException as exc:
        raise ModelGatewayError(
            status_code=504,
            error_type="gateway_timeout",
            message=(
                "The streaming model request "
                "exceeded the configured timeout."
            ),
        ) from exc

    except httpx.RequestError as exc:
        raise ModelGatewayError(
            status_code=502,
            error_type="gateway_connection_error",
            message=(
                "FastAPI could not connect to LiteLLM."
            ),
        ) from exc

    total_latency = round(
        time.perf_counter() - started_at,
        3,
    )

    ttft_seconds = None

    if first_token_at is not None:
        ttft_seconds = round(
            first_token_at - started_at,
            3,
        )

    yield {
        "type": "completed",
        "request_id": request_id,
        "model_id": model_config.public_id,
        "actual_model": actual_model,
        "display_name": model_config.display_name,
        "provider": model_config.provider,
        "finish_reason": finish_reason,
        "usage": usage_to_dict(final_usage),
        "ttft_seconds": ttft_seconds,
        "total_latency_seconds": total_latency,
        "message_count": len(request.messages),
    }