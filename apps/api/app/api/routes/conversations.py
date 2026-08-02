from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageResponse,
)
from app.services.conversation_service import (
    create_user_conversation,
    delete_user_conversation,
    get_user_conversation,
    list_conversation_messages,
    list_user_conversations,
    update_user_conversation,
)


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


def conversation_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
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


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    request: ConversationCreateRequest,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> ConversationResponse:
    conversation = create_user_conversation(
        database_session=database_session,
        user_id=current_user.id,
        title=request.title,
        model_id=request.model_id,
    )

    return ConversationResponse.model_validate(
        conversation
    )


@router.get(
    "",
    response_model=list[ConversationResponse],
)
def list_conversations(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
    include_archived: Annotated[
        bool,
        Query(),
    ] = False,
) -> list[ConversationResponse]:
    conversations = list_user_conversations(
        database_session=database_session,
        user_id=current_user.id,
        include_archived=include_archived,
    )

    return [
        ConversationResponse.model_validate(
            conversation
        )
        for conversation in conversations
    ]


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def read_conversation(
    conversation_id: UUID,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> ConversationDetailResponse:
    conversation = get_user_conversation(
        database_session=database_session,
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise conversation_not_found()

    messages = list_conversation_messages(
        database_session=database_session,
        conversation_id=conversation.id,
    )

    return ConversationDetailResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        model_id=conversation.model_id,
        is_archived=conversation.is_archived,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse.model_validate(
                message
            )
            for message in messages
        ],
    )


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def read_conversation_messages(
    conversation_id: UUID,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> list[MessageResponse]:
    conversation = get_user_conversation(
        database_session=database_session,
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise conversation_not_found()

    messages = list_conversation_messages(
        database_session=database_session,
        conversation_id=conversation.id,
    )

    return [
        MessageResponse.model_validate(
            message
        )
        for message in messages
    ]


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def update_conversation(
    conversation_id: UUID,
    request: ConversationUpdateRequest,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> ConversationResponse:
    conversation = get_user_conversation(
        database_session=database_session,
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise conversation_not_found()

    changes = request.model_dump(
        exclude_unset=True
    )

    conversation = update_user_conversation(
        database_session=database_session,
        conversation=conversation,
        changes=changes,
    )

    return ConversationResponse.model_validate(
        conversation
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    database_session: Annotated[
        Session,
        Depends(get_db),
    ],
) -> Response:
    conversation = get_user_conversation(
        database_session=database_session,
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    if conversation is None:
        raise conversation_not_found()

    delete_user_conversation(
        database_session=database_session,
        conversation=conversation,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
