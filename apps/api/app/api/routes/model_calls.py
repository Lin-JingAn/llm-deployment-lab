from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.model_call import (
    ModelCallListResponse,
    ModelCallResponse,
    ModelCallSummaryResponse,
)
from app.services.model_call_query_service import (
    get_user_model_call_summary,
    list_user_model_calls,
)


router = APIRouter(
    prefix="/model-calls",
    tags=["Model Calls"],
)


@router.get(
    "",
    response_model=ModelCallListResponse,
)
def read_model_calls(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    call_status: Annotated[
        Literal["success", "failed"] | None,
        Query(alias="status"),
    ] = None,
    requested_model: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
    provider: Annotated[
        str | None,
        Query(min_length=1, max_length=100),
    ] = None,
) -> ModelCallListResponse:
    items, total = list_user_model_calls(
        database_session=database_session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        call_status=call_status,
        requested_model=requested_model,
        provider=provider,
    )

    return ModelCallListResponse(
        items=[
            ModelCallResponse.model_validate(item)
            for item in items
        ],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )


@router.get(
    "/summary",
    response_model=ModelCallSummaryResponse,
)
def read_model_call_summary(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> ModelCallSummaryResponse:
    summary = get_user_model_call_summary(
        database_session=database_session,
        user_id=current_user.id,
    )

    return ModelCallSummaryResponse(
        **summary
    )
