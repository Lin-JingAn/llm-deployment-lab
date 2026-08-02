# API reference

Base URL: `http://127.0.0.1:8002`

Authenticated endpoints require:

```http
Authorization: Bearer <access-token>
```

## Authentication

### POST /auth/register

Creates a user account.

### POST /auth/login

Returns a JWT access token and safe user profile.

### GET /auth/me

Returns the authenticated user.

## Models and chat

### GET /models

Returns enabled public model definitions.

### POST /chat

Runs a non-streaming chat request. The request may include `conversation_id`. When omitted, the backend creates a new conversation and returns its ID.

### POST /chat/stream

Returns Server-Sent Events for a streaming model response.

## Conversations

### POST /conversations

Creates an empty user-owned conversation.

### GET /conversations

Lists the current user's conversations.

### GET /conversations/{conversation_id}

Returns a conversation and its ordered messages.

### PATCH /conversations/{conversation_id}

Updates the title, selected model, or archive state.

### DELETE /conversations/{conversation_id}

Deletes the conversation and cascades its messages.

### GET /conversations/{conversation_id}/messages

Returns the ordered messages for the conversation.

## Model-call metrics

### GET /model-calls

Returns paginated model-call records belonging to the authenticated user.

### GET /model-calls/summary

Returns aggregate call count, success and failure totals, token totals, and latency statistics.

## Health

### GET /health

Checks the FastAPI process.

### GET /health/readiness

Checks whether FastAPI can reach LiteLLM.
