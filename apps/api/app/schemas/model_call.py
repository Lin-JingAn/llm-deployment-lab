from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ModelCallResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    request_id: str | None

    requested_model: str
    actual_model: str | None
    provider: str | None

    mode: str
    status: str
    finish_reason: str | None

    error_type: str | None
    error_message: str | None

    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_tokens: int
    cached_tokens: int

    ttft_seconds: float | None
    total_latency_seconds: float | None

    message_count: int
    created_at: datetime


class ModelCallListResponse(BaseModel):
    items: list[ModelCallResponse]

    total: int
    limit: int
    offset: int
    has_more: bool


class ModelCallModelSummary(BaseModel):
    requested_model: str
    provider: str | None

    calls: int
    success_calls: int
    failed_calls: int
    total_tokens: int


class ModelCallSummaryResponse(BaseModel):
    total_calls: int
    success_calls: int
    failed_calls: int

    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_tokens: int
    cached_tokens: int

    average_latency_seconds: float | None

    models: list[ModelCallModelSummary]
