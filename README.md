# Unified LLM Platform

A multi-provider large-language-model application built with FastAPI, LiteLLM, PostgreSQL, SQLAlchemy, Alembic, and a browser-based frontend.

## Current version

The current implementation includes:

- Unified model access through LiteLLM.
- FastAPI application gateway on port `8002`.
- User registration, login, and JWT authentication.
- Persistent conversations and messages.
- Conversation history restoration after browser refresh.
- Per-user model-call records.
- Token, latency, provider, status, and failure statistics.
- Static browser frontend on port `5500`.
- Direct proxy service on port `8899`.
- Docker services for LiteLLM and PostgreSQL.

## Architecture

```text
Browser :5500
    |
    v
FastAPI :8002
    |-- JWT authentication
    |-- conversation persistence
    |-- model-call logging
    |
    v
LiteLLM :4000
    |
    +--> Alibaba Cloud Bailian
    +--> DeepSeek
    +--> other configured providers

PostgreSQL :5433
    +-- users
    +-- conversations
    +-- messages
    +-- model_calls
```

Detailed architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Project structure

```text
apps/
  api/                  FastAPI backend and Alembic migrations
  web/                  Static frontend, authentication, chat and usage pages
infra/
  litellm/              Docker Compose configuration for LiteLLM and PostgreSQL
tools/
  direct_proxy.py       Direct-provider proxy used by the local gateway
scripts/
  start-platform.ps1    Start local services without duplicating occupied ports
  stop-platform.ps1     Stop local application services and preserve database data
  health-check.ps1      Check ports and HTTP health endpoints
  security-scan.ps1     Scan source files for possible committed secrets
docs/
  ARCHITECTURE.md
  API.md
  RESUME_PROJECT.md
```

## Environment setup

Create local environment files:

```powershell
Copy-Item apps\api\.env.example apps\api\.env
Copy-Item infra\litellm\.env.example infra\litellm\.env
```

Replace every `replace-me` value locally. Never commit real `.env` files.

## Python environment

```powershell
cd D:\AI\llm-deployment-lab\apps\api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For exact reproduction of the current environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```

## Database migrations

Start PostgreSQL first, then run:

```powershell
cd D:\AI\llm-deployment-lab\apps\api
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Current tables:

- `users`
- `conversations`
- `messages`
- `model_calls`

## Start the platform

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-platform.ps1
```

The script starts only missing local services and does not duplicate an occupied port.

Main URLs:

- Web application: `http://127.0.0.1:5500`
- FastAPI documentation: `http://127.0.0.1:8002/docs`
- Usage dashboard: `http://127.0.0.1:5500/usage.html`
- LiteLLM gateway: `http://127.0.0.1:4000`

## Health check

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\health-check.ps1
```

## Stop the platform

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop-platform.ps1
```

The stop script uses `docker compose stop`; it does not delete PostgreSQL volumes.

## API overview

See [`docs/API.md`](docs/API.md).

Core endpoints include:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /models`
- `POST /chat`
- `POST /chat/stream`
- `GET|POST /conversations`
- `GET|PATCH|DELETE /conversations/{conversation_id}`
- `GET /conversations/{conversation_id}/messages`
- `GET /model-calls`
- `GET /model-calls/summary`
- `GET /health`
- `GET /health/readiness`

## Security before GitHub upload

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\security-scan.ps1
```

The repository-level `.gitignore` excludes `.env`, virtual environments, backups, caches, and local runtime files. Review `git status` before every push.

## Resume material

A concise Chinese resume description and interview talking points are available in [`docs/RESUME_PROJECT.md`](docs/RESUME_PROJECT.md).
