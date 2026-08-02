# Architecture

## Request flow

1. The browser loads the static frontend from port `5500`.
2. Authentication requests are sent to FastAPI on port `8002`.
3. FastAPI validates the JWT and resolves the current user.
4. Chat requests are normalized into the platform's common schema.
5. FastAPI sends the request to LiteLLM on port `4000`.
6. LiteLLM routes the request to the configured model provider.
7. FastAPI records the model call in PostgreSQL.
8. User and assistant messages are persisted under the active conversation.
9. The frontend uses the returned `conversation_id` to continue the same conversation.

## Backend layers

- `api/routes`: HTTP endpoints and request dependencies.
- `schemas`: Pydantic request and response models.
- `services`: authentication, model gateway, conversation persistence, and metrics logic.
- `models`: SQLAlchemy database models.
- `db`: engine and session management.
- `alembic`: database schema migrations.

## Data model

### users

Stores account identity, password hash, role, activation state, and timestamps.

### conversations

Stores user ownership, title, selected model, archive state, and timestamps.

### messages

Stores ordered user and assistant messages. Assistant messages may reference a `model_calls` record.

### model_calls

Stores provider, requested and actual model, request status, token usage, latency, finish reason, and error details.

## Security boundaries

- Password hashes are never returned by API responses.
- Chat, conversation, and usage endpoints require a valid bearer token.
- Conversation queries enforce user ownership.
- Model-call queries are restricted to the authenticated user.
- Provider credentials remain in ignored `.env` files.
