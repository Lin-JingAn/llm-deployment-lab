from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def derive_conversation_title(
    content: str,
) -> str:
    normalized = " ".join(
        content.split()
    )

    if not normalized:
        return "New conversation"

    return normalized[:80]


def create_user_conversation(
    *,
    database_session: Session,
    user_id: UUID,
    title: str | None = None,
    model_id: str | None = None,
) -> Conversation:
    conversation = Conversation(
        user_id=user_id,
        title=title or "New conversation",
        model_id=model_id,
    )

    try:
        database_session.add(conversation)
        database_session.commit()
        database_session.refresh(conversation)

        return conversation

    except Exception:
        database_session.rollback()
        raise


def get_user_conversation(
    *,
    database_session: Session,
    user_id: UUID,
    conversation_id: UUID,
) -> Conversation | None:
    return database_session.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )


def list_user_conversations(
    *,
    database_session: Session,
    user_id: UUID,
    include_archived: bool = False,
) -> list[Conversation]:
    statement = select(
        Conversation
    ).where(
        Conversation.user_id == user_id
    )

    if not include_archived:
        statement = statement.where(
            Conversation.is_archived.is_(False)
        )

    statement = statement.order_by(
        Conversation.updated_at.desc(),
        Conversation.created_at.desc(),
    )

    return list(
        database_session.scalars(
            statement
        ).all()
    )


def update_user_conversation(
    *,
    database_session: Session,
    conversation: Conversation,
    changes: dict[str, Any],
) -> Conversation:
    for field_name in (
        "title",
        "model_id",
        "is_archived",
    ):
        if field_name in changes:
            setattr(
                conversation,
                field_name,
                changes[field_name],
            )

    conversation.updated_at = utc_now()

    try:
        database_session.add(conversation)
        database_session.commit()
        database_session.refresh(conversation)

        return conversation

    except Exception:
        database_session.rollback()
        raise


def delete_user_conversation(
    *,
    database_session: Session,
    conversation: Conversation,
) -> None:
    try:
        database_session.delete(conversation)
        database_session.commit()

    except Exception:
        database_session.rollback()
        raise


def list_conversation_messages(
    *,
    database_session: Session,
    conversation_id: UUID,
) -> list[Message]:
    return list(
        database_session.scalars(
            select(Message)
            .where(
                Message.conversation_id
                == conversation_id
            )
            .order_by(
                Message.sequence_number.asc()
            )
        ).all()
    )


def append_conversation_message(
    *,
    database_session: Session,
    user_id: UUID,
    conversation_id: UUID,
    role: str,
    content: str,
    model_call_id: UUID | None = None,
    model_id: str | None = None,
    provider: str | None = None,
) -> Message:
    conversation = database_session.scalar(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .with_for_update()
    )

    if conversation is None:
        raise LookupError(
            "Conversation was not found."
        )

    current_maximum = database_session.scalar(
        select(
            func.coalesce(
                func.max(
                    Message.sequence_number
                ),
                0,
            )
        ).where(
            Message.conversation_id
            == conversation_id
        )
    )

    sequence_number = int(
        current_maximum or 0
    ) + 1

    message = Message(
        conversation_id=conversation_id,
        model_call_id=model_call_id,
        role=role,
        content=content,
        sequence_number=sequence_number,
        model_id=model_id,
        provider=provider,
    )

    conversation.updated_at = utc_now()

    if model_id is not None:
        conversation.model_id = model_id

    try:
        database_session.add(message)
        database_session.add(conversation)
        database_session.commit()

        database_session.refresh(message)
        database_session.refresh(conversation)

        return message

    except Exception:
        database_session.rollback()
        raise
