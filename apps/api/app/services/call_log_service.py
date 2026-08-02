from uuid import UUID

from sqlalchemy.orm import Session

from app.models.model_call import ModelCall


def record_model_call(
    *,
    database_session: Session,
    user_id: UUID,
    requested_model: str,
    mode: str,
    message_count: int,
    status: str,
    request_id: str | None = None,
    actual_model: str | None = None,
    provider: str | None = None,
    finish_reason: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    reasoning_tokens: int = 0,
    cached_tokens: int = 0,
    ttft_seconds: float | None = None,
    total_latency_seconds: float | None = None,
) -> ModelCall | None:
    model_call = ModelCall(
        user_id=user_id,
        request_id=request_id,
        requested_model=requested_model,
        actual_model=actual_model,
        provider=provider,
        mode=mode,
        status=status,
        finish_reason=finish_reason,
        error_type=error_type,
        error_message=error_message,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        reasoning_tokens=reasoning_tokens,
        cached_tokens=cached_tokens,
        ttft_seconds=ttft_seconds,
        total_latency_seconds=(
            total_latency_seconds
        ),
        message_count=message_count,
    )

    try:
        database_session.add(model_call)
        database_session.commit()
        database_session.refresh(model_call)

        return model_call

    except Exception:
        database_session.rollback()

        return None
