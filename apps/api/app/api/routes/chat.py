import json
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.model_registry import (
    ModelConfig,
    get_enabled_models,
    get_model_config,
)
from app.db.session import SessionLocal, get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ModelInfo,
    ModelsResponse,
)
from app.services.call_log_service import (
    record_model_call,
)
from app.services.conversation_service import (
    append_conversation_message,
    create_user_conversation,
    derive_conversation_title,
    get_user_conversation,
)
from app.services.model_gateway import (
    ModelGatewayError,
    create_chat_completion,
    stream_chat_completion,
)


router = APIRouter(
    tags=["Model Gateway"],
)


def resolve_model(
    model_id: str,
) -> ModelConfig:
    try:
        return get_model_config(model_id)

    except KeyError as exc:
        available_models = [
            model.public_id
            for model in get_enabled_models()
        ]

        raise HTTPException(
            status_code=404,
            detail={
                "message": (
                    f"Model '{model_id}' "
                    "is not registered."
                ),
                "error_type": "model_not_found",
                "available_models": available_models,
            },
        ) from exc

    except PermissionError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": (
                    f"Model '{model_id}' "
                    "is currently disabled."
                ),
                "error_type": "model_disabled",
            },
        ) from exc


def convert_gateway_error(
    error: ModelGatewayError,
) -> HTTPException:
    detail: dict[str, Any] = {
        "message": error.message,
        "error_type": error.error_type,
    }

    if error.upstream_status_code is not None:
        detail["upstream_status_code"] = (
            error.upstream_status_code
        )

    if (
        settings.environment == "development"
        and error.upstream_body
    ):
        detail["upstream_response"] = (
            error.upstream_body
        )

    return HTTPException(
        status_code=error.status_code,
        detail=detail,
    )


def encode_sse(
    event: dict[str, Any],
) -> str:
    return (
        "data: "
        + json.dumps(
            event,
            ensure_ascii=False,
        )
        + "\n\n"
    )


def integer_value(
    value: Any,
) -> int:
    if value is None:
        return 0

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return 0


def get_latest_user_message(
    request: ChatRequest,
) -> str:
    for message in reversed(
        request.messages
    ):
        if message.role == "user":
            return message.content

    raise HTTPException(
        status_code=400,
        detail={
            "message": (
                "A chat request must contain "
                "at least one user message."
            ),
            "error_type": (
                "user_message_required"
            ),
        },
    )


def resolve_conversation(
    *,
    database_session: Session,
    current_user: User,
    request: ChatRequest,
    user_message: str,
) -> Conversation:
    if request.conversation_id is not None:
        conversation = get_user_conversation(
            database_session=database_session,
            user_id=current_user.id,
            conversation_id=(
                request.conversation_id
            ),
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": (
                        "The requested conversation "
                        "was not found."
                    ),
                    "error_type": (
                        "conversation_not_found"
                    ),
                },
            )

        return conversation

    return create_user_conversation(
        database_session=database_session,
        user_id=current_user.id,
        title=derive_conversation_title(
            user_message
        ),
        model_id=request.model,
    )


def persist_user_message(
    *,
    database_session: Session,
    current_user: User,
    conversation: Conversation,
    request: ChatRequest,
    user_message: str,
) -> None:
    append_conversation_message(
        database_session=database_session,
        user_id=current_user.id,
        conversation_id=conversation.id,
        role="user",
        content=user_message,
        model_id=request.model,
    )


@router.get(
    "/models",
    response_model=ModelsResponse,
)
async def list_models() -> ModelsResponse:
    enabled_models = get_enabled_models()

    models = [
        ModelInfo(
            id=model.public_id,
            display_name=model.display_name,
            provider=model.provider,
            enabled=model.enabled,
            is_default=(
                model.public_id
                == settings.default_model_id
            ),
            supports_streaming=(
                model.supports_streaming
            ),
            supports_reasoning=(
                model.supports_reasoning
            ),
            supports_tools=model.supports_tools,
            supports_vision=model.supports_vision,
            default_max_output_tokens=(
                model.default_max_output_tokens
            ),
            max_output_tokens=(
                model.max_output_tokens
            ),
        )
        for model in enabled_models
    ]

    return ModelsResponse(
        default_model=settings.default_model_id,
        models=models,
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> ChatResponse:
    if request.stream:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Use /chat/stream for "
                    "streaming responses."
                ),
                "error_type": (
                    "incorrect_stream_endpoint"
                ),
            },
        )

    model_config = resolve_model(
        request.model
    )

    user_message = get_latest_user_message(
        request
    )

    conversation = resolve_conversation(
        database_session=database_session,
        current_user=current_user,
        request=request,
        user_message=user_message,
    )

    persist_user_message(
        database_session=database_session,
        current_user=current_user,
        conversation=conversation,
        request=request,
        user_message=user_message,
    )

    try:
        response = await create_chat_completion(
            request=request,
            model_config=model_config,
        )

        usage = response.usage

        model_call = record_model_call(
            database_session=database_session,
            user_id=current_user.id,
            requested_model=request.model,
            actual_model=response.actual_model,
            provider=(
                response.provider
                or model_config.provider
            ),
            mode=request.mode,
            status="success",
            request_id=response.request_id,
            finish_reason=(
                response.finish_reason
            ),
            input_tokens=integer_value(
                usage.input_tokens
            ),
            output_tokens=integer_value(
                usage.output_tokens
            ),
            total_tokens=integer_value(
                usage.total_tokens
            ),
            reasoning_tokens=integer_value(
                usage.reasoning_tokens
            ),
            cached_tokens=integer_value(
                usage.cached_tokens
            ),
            ttft_seconds=response.ttft_seconds,
            total_latency_seconds=(
                response.total_latency_seconds
            ),
            message_count=len(
                request.messages
            ),
        )

        append_conversation_message(
            database_session=database_session,
            user_id=current_user.id,
            conversation_id=conversation.id,
            role="assistant",
            content=response.reply,
            model_call_id=(
                model_call.id
                if model_call is not None
                else None
            ),
            model_id=response.model_id,
            provider=response.provider,
        )

        return response.model_copy(
            update={
                "conversation_id":
                    conversation.id,
            }
        )

    except ModelGatewayError as error:
        record_model_call(
            database_session=database_session,
            user_id=current_user.id,
            requested_model=request.model,
            provider=model_config.provider,
            mode=request.mode,
            status="failed",
            error_type=error.error_type,
            error_message=error.message,
            message_count=len(
                request.messages
            ),
        )

        raise convert_gateway_error(
            error
        ) from error


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> StreamingResponse:
    model_config = resolve_model(
        request.model
    )

    if not model_config.supports_streaming:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    f"Model '{request.model}' "
                    "does not support streaming."
                ),
                "error_type": (
                    "streaming_not_supported"
                ),
            },
        )

    user_message = get_latest_user_message(
        request
    )

    conversation = resolve_conversation(
        database_session=database_session,
        current_user=current_user,
        request=request,
        user_message=user_message,
    )

    persist_user_message(
        database_session=database_session,
        current_user=current_user,
        conversation=conversation,
        request=request,
        user_message=user_message,
    )

    current_user_id = current_user.id
    conversation_id = conversation.id

    async def event_generator() -> AsyncIterator[str]:
        completed_event: dict[str, Any] | None = None
        assistant_content_parts: list[str] = []

        try:
            async for event in stream_chat_completion(
                request=request,
                model_config=model_config,
            ):
                event = dict(event)

                event["conversation_id"] = str(
                    conversation_id
                )

                if event.get("type") == "content_delta":
                    content = event.get("content")

                    if content:
                        assistant_content_parts.append(
                            str(content)
                        )

                if event.get("type") == "completed":
                    completed_event = event

                yield encode_sse(event)

            if completed_event is not None:
                usage = (
                    completed_event.get("usage")
                    or {}
                )

                with SessionLocal() as log_session:
                    model_call = record_model_call(
                        database_session=log_session,
                        user_id=current_user_id,
                        requested_model=request.model,
                        actual_model=(
                            completed_event.get(
                                "actual_model"
                            )
                        ),
                        provider=(
                            completed_event.get(
                                "provider"
                            )
                            or model_config.provider
                        ),
                        mode=request.mode,
                        status="success",
                        request_id=(
                            completed_event.get(
                                "request_id"
                            )
                        ),
                        finish_reason=(
                            completed_event.get(
                                "finish_reason"
                            )
                        ),
                        input_tokens=integer_value(
                            usage.get(
                                "input_tokens",
                                0,
                            )
                        ),
                        output_tokens=integer_value(
                            usage.get(
                                "output_tokens",
                                0,
                            )
                        ),
                        total_tokens=integer_value(
                            usage.get(
                                "total_tokens",
                                0,
                            )
                        ),
                        reasoning_tokens=integer_value(
                            usage.get(
                                "reasoning_tokens",
                                0,
                            )
                        ),
                        cached_tokens=integer_value(
                            usage.get(
                                "cached_tokens",
                                0,
                            )
                        ),
                        ttft_seconds=(
                            completed_event.get(
                                "ttft_seconds"
                            )
                        ),
                        total_latency_seconds=(
                            completed_event.get(
                                "total_latency_seconds"
                            )
                        ),
                        message_count=len(
                            request.messages
                        ),
                    )

                    assistant_content = "".join(
                        assistant_content_parts
                    )

                    if assistant_content:
                        append_conversation_message(
                            database_session=log_session,
                            user_id=current_user_id,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=assistant_content,
                            model_call_id=(
                                model_call.id
                                if model_call is not None
                                else None
                            ),
                            model_id=request.model,
                            provider=(
                                completed_event.get(
                                    "provider"
                                )
                                or model_config.provider
                            ),
                        )

        except ModelGatewayError as error:
            with SessionLocal() as log_session:
                record_model_call(
                    database_session=log_session,
                    user_id=current_user_id,
                    requested_model=request.model,
                    provider=model_config.provider,
                    mode=request.mode,
                    status="failed",
                    error_type=error.error_type,
                    error_message=error.message,
                    message_count=len(
                        request.messages
                    ),
                )

            error_event: dict[str, Any] = {
                "type": "error",
                "conversation_id": str(
                    conversation_id
                ),
                "error_type": error.error_type,
                "message": error.message,
            }

            if error.upstream_status_code is not None:
                error_event[
                    "upstream_status_code"
                ] = error.upstream_status_code

            yield encode_sse(error_event)

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
