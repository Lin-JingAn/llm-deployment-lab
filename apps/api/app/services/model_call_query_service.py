from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.model_call import ModelCall


def build_model_call_filters(
    *,
    user_id: UUID,
    call_status: str | None = None,
    requested_model: str | None = None,
    provider: str | None = None,
) -> list:
    filters = [
        ModelCall.user_id == user_id,
    ]

    if call_status:
        filters.append(
            ModelCall.status == call_status
        )

    if requested_model:
        filters.append(
            ModelCall.requested_model
            == requested_model
        )

    if provider:
        filters.append(
            ModelCall.provider == provider
        )

    return filters


def list_user_model_calls(
    *,
    database_session: Session,
    user_id: UUID,
    limit: int,
    offset: int,
    call_status: str | None = None,
    requested_model: str | None = None,
    provider: str | None = None,
) -> tuple[list[ModelCall], int]:
    filters = build_model_call_filters(
        user_id=user_id,
        call_status=call_status,
        requested_model=requested_model,
        provider=provider,
    )

    total = int(
        database_session.scalar(
            select(func.count(ModelCall.id))
            .where(*filters)
        )
        or 0
    )

    items = list(
        database_session.scalars(
            select(ModelCall)
            .where(*filters)
            .order_by(
                ModelCall.created_at.desc(),
                ModelCall.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        ).all()
    )

    return items, total


def get_user_model_call_summary(
    *,
    database_session: Session,
    user_id: UUID,
) -> dict:
    success_case = case(
        (ModelCall.status == "success", 1),
        else_=0,
    )

    failed_case = case(
        (ModelCall.status == "failed", 1),
        else_=0,
    )

    latency_case = case(
        (
            ModelCall.status == "success",
            ModelCall.total_latency_seconds,
        ),
        else_=None,
    )

    summary_row = database_session.execute(
        select(
            func.count(ModelCall.id).label(
                "total_calls"
            ),
            func.coalesce(
                func.sum(success_case),
                0,
            ).label("success_calls"),
            func.coalesce(
                func.sum(failed_case),
                0,
            ).label("failed_calls"),
            func.coalesce(
                func.sum(ModelCall.input_tokens),
                0,
            ).label("input_tokens"),
            func.coalesce(
                func.sum(ModelCall.output_tokens),
                0,
            ).label("output_tokens"),
            func.coalesce(
                func.sum(ModelCall.total_tokens),
                0,
            ).label("total_tokens"),
            func.coalesce(
                func.sum(ModelCall.reasoning_tokens),
                0,
            ).label("reasoning_tokens"),
            func.coalesce(
                func.sum(ModelCall.cached_tokens),
                0,
            ).label("cached_tokens"),
            func.avg(latency_case).label(
                "average_latency_seconds"
            ),
        )
        .where(ModelCall.user_id == user_id)
    ).mappings().one()

    call_count = func.count(
        ModelCall.id
    ).label("calls")

    model_rows = database_session.execute(
        select(
            ModelCall.requested_model,
            ModelCall.provider,
            call_count,
            func.coalesce(
                func.sum(success_case),
                0,
            ).label("success_calls"),
            func.coalesce(
                func.sum(failed_case),
                0,
            ).label("failed_calls"),
            func.coalesce(
                func.sum(ModelCall.total_tokens),
                0,
            ).label("total_tokens"),
        )
        .where(ModelCall.user_id == user_id)
        .group_by(
            ModelCall.requested_model,
            ModelCall.provider,
        )
        .order_by(
            call_count.desc(),
            ModelCall.requested_model.asc(),
        )
        .limit(50)
    ).mappings().all()

    average_latency = summary_row[
        "average_latency_seconds"
    ]

    return {
        "total_calls": int(
            summary_row["total_calls"] or 0
        ),
        "success_calls": int(
            summary_row["success_calls"] or 0
        ),
        "failed_calls": int(
            summary_row["failed_calls"] or 0
        ),
        "input_tokens": int(
            summary_row["input_tokens"] or 0
        ),
        "output_tokens": int(
            summary_row["output_tokens"] or 0
        ),
        "total_tokens": int(
            summary_row["total_tokens"] or 0
        ),
        "reasoning_tokens": int(
            summary_row["reasoning_tokens"] or 0
        ),
        "cached_tokens": int(
            summary_row["cached_tokens"] or 0
        ),
        "average_latency_seconds": (
            round(float(average_latency), 3)
            if average_latency is not None
            else None
        ),
        "models": [
            {
                "requested_model": row[
                    "requested_model"
                ],
                "provider": row["provider"],
                "calls": int(row["calls"] or 0),
                "success_calls": int(
                    row["success_calls"] or 0
                ),
                "failed_calls": int(
                    row["failed_calls"] or 0
                ),
                "total_tokens": int(
                    row["total_tokens"] or 0
                ),
            }
            for row in model_rows
        ],
    }
