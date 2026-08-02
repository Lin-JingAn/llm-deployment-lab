from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=200,
    )

    model_id: str | None = Field(
        default=None,
        max_length=100,
    )

    @field_validator("title")
    @classmethod
    def normalize_title(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(
            value.split()
        )

        return normalized or None


class ConversationUpdateRequest(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=200,
    )

    model_id: str | None = Field(
        default=None,
        max_length=100,
    )

    is_archived: bool | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(
            value.split()
        )

        if not normalized:
            raise ValueError(
                "Conversation title cannot be empty."
            )

        return normalized


class MessageResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    conversation_id: UUID
    model_call_id: UUID | None

    role: str
    content: str
    sequence_number: int

    model_id: str | None
    provider: str | None

    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    user_id: UUID

    title: str
    model_id: str | None
    is_archived: bool

    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(
    ConversationResponse
):
    messages: list[MessageResponse]
