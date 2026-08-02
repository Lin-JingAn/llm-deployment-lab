from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import settings


ChatRole = Literal[
    "system",
    "user",
    "assistant",
]

ChatMode = Literal[
    "fast",
    "reasoning",
]


class ChatMessage(BaseModel):
    role: ChatRole

    content: str = Field(
        min_length=1,
        max_length=20000,
        description=(
            "The content of one conversation message."
        ),
    )


class ChatRequest(BaseModel):
    conversation_id: UUID | None = Field(
        default=None,
        description=(
            "Existing conversation ID. "
            "When omitted, a new conversation is created."
        ),
    )

    model: str = Field(
        default=settings.default_model_id,
        min_length=1,
        max_length=100,
        description=(
            "The public model ID used by the platform."
        ),
    )

    messages: list[ChatMessage] = Field(
        min_length=1,
        max_length=settings.max_conversation_messages,
        description=(
            "Conversation messages in chronological order."
        ),
    )

    mode: ChatMode = Field(
        default="fast",
        description="fast or reasoning.",
    )

    stream: bool = Field(
        default=False,
        description=(
            "Whether to return a streaming response."
        ),
    )

    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
    )

    max_output_tokens: int | None = Field(
        default=None,
        ge=1,
        le=32768,
    )

    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=32768,
        description=(
            "Legacy output-token field used by "
            "the current web client."
        ),
    )


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    reasoning_tokens: int = 0
    cached_tokens: int = 0


class ChatResponse(BaseModel):
    request_id: str
    conversation_id: UUID | None = None

    model_id: str
    actual_model: str
    display_name: str
    provider: str

    reply: str

    reasoning_content: str | None = None
    finish_reason: str | None = None

    usage: TokenUsage

    ttft_seconds: float | None = None
    total_latency_seconds: float

    message_count: int


class ModelInfo(BaseModel):
    id: str
    display_name: str
    provider: str

    enabled: bool
    is_default: bool

    supports_streaming: bool
    supports_reasoning: bool
    supports_tools: bool
    supports_vision: bool

    default_max_output_tokens: int
    max_output_tokens: int


class ModelsResponse(BaseModel):
    default_model: str
    models: list[ModelInfo]
