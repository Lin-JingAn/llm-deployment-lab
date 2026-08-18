# Unified LLM Platform

A multi-provider LLM application and serving platform that unifies cloud model APIs and self-hosted open-weight models behind a single application interface.

The platform is built with **FastAPI, LiteLLM, PostgreSQL, Docker, vLLM, and a browser-based frontend**. It currently supports cloud model providers such as **Alibaba Cloud Bailian / Qwen** and **DeepSeek**, as well as a self-hosted **Qwen2.5-7B-Instruct** model served on a Linux GPU server through **vLLM**.

The project is designed around a simple idea:

> Application code should not need to know whether a model is running in a cloud provider or on a local GPU server.

Instead, FastAPI handles application logic, LiteLLM provides a unified model gateway, and the underlying model can be either a cloud API or a self-hosted inference service.

---

## Overview

Modern LLM applications often depend on multiple model providers.

Different providers expose different:

- API endpoints
- authentication methods
- model identifiers
- request parameters
- response formats
- token accounting behavior
- failure modes

At the same time, self-hosted models introduce an entirely different deployment path involving:

- model weights
- GPU memory
- CUDA
- inference engines
- networking
- service endpoints

Without an abstraction layer, application code can quickly become tightly coupled to specific model providers.

This project introduces a unified architecture:

```text
Application
    |
    v
FastAPI
    |
    v
LiteLLM
    |
    +--------------------+
    |                    |
    v                    v
Cloud APIs          Local Serving
                         |
                         v
                       vLLM
                         |
                         v
                  Qwen2.5-7B
```

The application therefore communicates with models through a consistent internal interface regardless of where the model actually runs.

---

## Current Status

The current implementation includes:

| Capability | Status |
|---|---|
| FastAPI application backend | ✅ Verified |
| Browser-based frontend | ✅ Verified |
| User registration and login | ✅ Verified |
| JWT authentication | ✅ Verified |
| Persistent conversations | ✅ Verified |
| Conversation history restoration | ✅ Verified |
| Per-user message isolation | ✅ Verified |
| PostgreSQL persistence | ✅ Verified |
| SQLAlchemy ORM | ✅ Verified |
| Alembic migrations | ✅ Verified |
| LiteLLM unified model gateway | ✅ Verified |
| Alibaba Cloud Bailian / Qwen integration | ✅ Verified |
| DeepSeek integration | ✅ Verified |
| Qwen2.5-7B-Instruct local deployment | ✅ Verified |
| vLLM inference serving | ✅ Verified |
| RTX 3090 GPU inference | ✅ Verified |
| Tailscale cross-host networking | ✅ Verified |
| LiteLLM Virtual Key model access control | ✅ Verified |
| Token usage tracking | ✅ Verified |
| Latency tracking | ✅ Verified |
| Provider / model call logging | ✅ Verified |
| Usage dashboard | ✅ Verified |
| Dockerized LiteLLM | ✅ Verified |
| Dockerized PostgreSQL | ✅ Verified |
| Proxy / NO_PROXY routing | ✅ Verified |
| Health-check scripts | ✅ Verified |
| Start / stop automation | ✅ Verified |
| Secret scanning helper | ✅ Verified |
| SGLang serving comparison | ⚠️ Evaluated, not part of the stable release |

---

## Architecture

```text
                               User
                                |
                                v
                       Browser Frontend
                            :5500
                                |
                                | HTTP
                                v
                         FastAPI Backend
                            :8002
                                |
               +----------------+----------------+
               |                |                |
               v                v                v
         Authentication    Conversations    Observability
              JWT              CRUD          Token / Latency
               |                |                |
               |                v                |
               |           PostgreSQL            |
               |             :5433               |
               |                                 |
               +----------------+----------------+
                                |
                                v
                         LiteLLM Gateway
                            :4000
                                |
                  +-------------+-------------+
                  |                           |
                  v                           v
              Cloud Models               Local Model
                  |                           |
          +-------+-------+                   |
          |               |                   |
          v               v                   v
 Alibaba Cloud        DeepSeek            Tailscale
 Bailian / Qwen                             Private
                                             Network
                                               |
                                               v
                                          Linux Server
                                               |
                                               v
                                             vLLM
                                             :8001
                                               |
                                               v
                                      Qwen2.5-7B-Instruct
                                               |
                                               v
                                          NVIDIA RTX 3090
```

Detailed architecture documentation:

[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Request Flow

A typical local-model request follows this path:

```text
User
 |
 v
Web Frontend
 |
 v
FastAPI
 |
 |-- authenticate user
 |-- resolve conversation
 |-- resolve model configuration
 |
 v
LiteLLM
 |
 |-- resolve upstream model
 |
 v
Tailscale Private Network
 |
 v
Linux GPU Server
 |
 v
vLLM
 |
 v
Qwen2.5-7B-Instruct
 |
 v
RTX 3090
 |
 v
Model Response
 |
 v
LiteLLM
 |
 v
FastAPI
 |
 |-- persist user message
 |-- persist assistant message
 |-- persist model call
 |-- record token usage
 |-- record latency
 |
 v
Web Frontend
```

The same FastAPI endpoint can also route requests to cloud models through LiteLLM.

---

## Core Design

### Application Layer — FastAPI

FastAPI is responsible for application-level business logic.

It handles:

- user registration
- login
- JWT authentication
- conversation ownership
- message persistence
- model selection
- model-call orchestration
- token and latency logging
- usage queries
- health endpoints

FastAPI does **not** run the LLM itself.

Its role is to coordinate application behavior around the model layer.

---

### Model Gateway — LiteLLM

LiteLLM acts as the unified model gateway.

Instead of implementing separate application logic for every model provider, FastAPI sends model requests through a common gateway.

Conceptually:

```text
FastAPI
    |
    v
LiteLLM
    |
    +--> Alibaba Cloud Bailian / Qwen
    |
    +--> DeepSeek
    |
    +--> Local vLLM
```

This separates application logic from provider-specific model integrations.

The architecture makes it easier to:

- add new model providers
- replace upstream models
- control model access
- introduce routing policies
- implement fallback strategies
- centralize usage tracking

---

## Supported Model Paths

### Cloud Models

The stable application currently includes cloud-model integration through LiteLLM.

Verified providers include:

- Alibaba Cloud Bailian / Qwen
- DeepSeek

Cloud requests follow:

```text
FastAPI
   |
   v
LiteLLM
   |
   v
Direct Proxy
   |
   v
Cloud Provider API
```

---

### Self-Hosted Model

The project also includes a self-hosted model path:

```text
Qwen2.5-7B-Instruct
        |
        v
      vLLM
        |
        v
   RTX 3090 GPU
```

The model is served on a Linux GPU server using vLLM.

vLLM exposes an OpenAI-compatible HTTP API, allowing LiteLLM to treat the local model as another upstream model provider.

---

## Why vLLM

Downloading model weights is not sufficient to make a model available to an application.

The model still needs an inference-serving layer responsible for:

- loading model weights
- moving model data to GPU memory
- managing inference requests
- handling KV cache
- generating tokens
- exposing network APIs
- serving multiple requests efficiently

vLLM provides this serving layer.

In this project:

```text
Model Weights
     |
     v
    vLLM
     |
     v
RTX 3090 GPU
     |
     v
OpenAI-Compatible API
```

This transforms the local Qwen model from a collection of model files into a remotely callable inference service.

---

## Local Model Deployment

The verified local deployment uses:

```text
Model:
Qwen2.5-7B-Instruct

Serving Engine:
vLLM

GPU:
NVIDIA GeForce RTX 3090

VRAM:
24 GB

Operating System:
Linux
```

The local serving endpoint runs independently from the Windows application machine.

The vLLM server provides an OpenAI-compatible API, allowing the model to be integrated into LiteLLM without introducing a separate application protocol.

---

## Cross-Host Networking with Tailscale

The application machine and the Linux GPU server are not located on the same directly routable local network.

Tailscale is used to create a private overlay network between the machines.

```text
Windows Application Host
          |
          | Tailscale
          v
Linux GPU Server
```

This allows LiteLLM on the Windows-side infrastructure to communicate with the vLLM server running on Linux.

The private server address is not hard-coded into the public repository.

Instead, it is supplied through an environment variable:

```env
LOCAL_VLLM_HOST=replace-me
```

This keeps runtime-specific infrastructure configuration separate from source code.

---

## Model Registry

The FastAPI application contains a central model registry.

Each public model defines metadata such as:

- public model ID
- upstream LiteLLM model ID
- display name
- provider
- enabled state
- streaming support
- reasoning support
- tool support
- vision support
- default temperature
- default output-token limit
- maximum output-token limit

Example model IDs currently include:

```text
qwen-plus

deepseek-v4-flash

qwen2.5-7b-local
```

This allows the application to expose a stable internal model interface while upstream implementations can change independently.

---

## Model Access Control

The application backend does not use the LiteLLM administrative master key for normal model calls.

Instead, a restricted LiteLLM Virtual Key is used.

Conceptually:

```text
FastAPI Application Key
        |
        +--> Qwen
        |
        +--> DeepSeek
        |
        +--> Qwen2.5-7B Local
```

When the local model was introduced, the application initially received a model-access denial because the existing virtual key only allowed the cloud models.

The key permissions were updated to include the local model while preserving the existing cloud-model permissions.

This keeps model access explicit and follows a least-privilege approach.

---

## Authentication

The platform supports:

- user registration
- user login
- JWT authentication
- authenticated API access
- per-user conversation isolation
- per-user model-call records

The authentication flow is:

```text
Email + Password
       |
       v
   FastAPI
       |
       v
Password Verification
       |
       v
     JWT
       |
       v
Authenticated Requests
```

Private endpoints require an authorization token.

---

## Conversation Persistence

Conversations and messages are persisted in PostgreSQL.

A typical message flow is:

```text
User Message
     |
     v
PostgreSQL
     |
     v
Model Call
     |
     v
Assistant Message
     |
     v
PostgreSQL
```

Because the conversation state is stored server-side, browser refreshes do not destroy the chat history.

The frontend can reload conversation data from the FastAPI API.

---

## Database

PostgreSQL is used for application persistence.

Current core tables include:

- `users`
- `conversations`
- `messages`
- `model_calls`

---

### `users`

Stores user identity and authentication-related information.

---

### `conversations`

Stores conversation metadata and ownership.

---

### `messages`

Stores ordered user and assistant messages associated with conversations.

---

### `model_calls`

Stores per-request model execution metadata such as:

- provider
- requested model
- actual model
- input tokens
- output tokens
- total tokens
- latency
- finish reason
- request status
- error information

---

## SQLAlchemy and Alembic

SQLAlchemy is used as the application ORM layer between Python and PostgreSQL.

Alembic is used to manage database schema migrations.

This allows database changes to be versioned rather than requiring manual table recreation.

Example migration command:

```powershell
cd apps\api

.\.venv\Scripts\python.exe -m alembic upgrade head
```

---

## Observability

Each model call can record:

- provider
- requested model
- actual model
- input tokens
- output tokens
- total tokens
- latency
- finish reason
- request status
- failure information

Example locally observed values include:

```text
Provider:
Local vLLM

Model:
Qwen2.5-7B Local

Input Tokens:
71

Output Tokens:
46

Total Tokens:
117

Response Latency:
3.29 seconds
```

This gives the application a basic model-observability layer rather than functioning as a simple chat interface only.

---

## Usage Dashboard

The browser frontend contains a dedicated usage page.

The dashboard exposes per-user model-call information such as:

- model
- provider
- token usage
- request status
- latency
- call history

This data can later support:

- provider comparison
- cost accounting
- model-performance analysis
- user-level quota systems
- operational monitoring

---

## Frontend

The frontend is implemented with:

- HTML
- CSS
- JavaScript

Current user-facing functionality includes:

- login
- registration
- model selection
- chat
- multi-turn conversations
- conversation history
- usage dashboard
- token display
- latency display
- provider display
- model metadata display

The frontend is intentionally lightweight so that the project focus remains on the model gateway and backend architecture.

---

## Proxy Architecture

The development environment includes a small direct-provider proxy service:

```text
tools/direct_proxy.py
```

It listens on port:

```text
8899
```

The proxy is used by LiteLLM for selected cloud-provider traffic.

Conceptually:

```text
LiteLLM Container
      |
      v
Direct Proxy :8899
      |
      v
Cloud Model APIs
```

This was introduced to handle development-network constraints involving Docker, VPN behavior, and provider connectivity.

---

## NO_PROXY Routing

Cloud traffic and local-model traffic follow different network paths.

Cloud providers may require the development proxy:

```text
LiteLLM
   |
   v
Proxy
   |
   v
Internet
```

The local vLLM server should not use this route.

Instead:

```text
LiteLLM
   |
   v
Tailscale
   |
   v
Linux vLLM
```

The LiteLLM container therefore uses `NO_PROXY` / `no_proxy` configuration to exclude:

- localhost
- loopback addresses
- the PostgreSQL container
- the local vLLM host

from proxy routing.

This prevents private Tailscale traffic from being incorrectly sent through the cloud-provider proxy.

---

## Docker

Docker is used to isolate and run infrastructure services.

Current Docker-managed services include:

```text
Docker
   |
   +--> LiteLLM
   |
   +--> PostgreSQL
```

This keeps infrastructure dependencies separated from the Windows application environment.

---

## Docker Compose

Docker Compose manages the LiteLLM and PostgreSQL services.

The main configuration file is:

```text
infra/litellm/compose.yaml
```

It defines:

- container images
- ports
- environment variables
- PostgreSQL credentials
- database connection
- proxy configuration
- container dependencies
- health checks
- restart behavior
- persistent database volumes

---

## Main Development Ports

| Port | Service |
|---|---|
| `5500` | Browser frontend |
| `8002` | FastAPI backend |
| `4000` | LiteLLM gateway |
| `5433` | PostgreSQL host mapping |
| `8899` | Direct cloud-provider proxy |
| `8001` | Linux vLLM inference server |

---

## Project Structure

```text
llm-deployment-lab/
|
|-- apps/
|   |
|   |-- api/
|   |   |
|   |   |-- app/
|   |   |   |-- api/          FastAPI route modules
|   |   |   |-- core/         Application configuration and model registry
|   |   |   |-- db/           Database configuration
|   |   |   |-- models/       SQLAlchemy models
|   |   |   |-- schemas/      Request / response schemas
|   |   |   `-- services/     Application services
|   |   |
|   |   |-- alembic/          Database migrations
|   |   |-- requirements.txt
|   |   `-- requirements.lock.txt
|   |
|   `-- web/
|       |-- index.html
|       |-- app.js
|       |-- chat.js
|       |-- styles.css
|       |-- login.html
|       |-- register.html
|       |-- auth.js
|       |-- auth.css
|       |-- usage.html
|       |-- usage.js
|       `-- usage.css
|
|-- infra/
|   `-- litellm/
|       |-- compose.yaml
|       `-- .env.example
|
|-- tools/
|   `-- direct_proxy.py
|
|-- scripts/
|   |-- start-platform.ps1
|   |-- stop-platform.ps1
|   |-- health-check.ps1
|   `-- security-scan.ps1
|
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- API.md
|   `-- RESUME_PROJECT.md
|
|-- .gitignore
`-- README.md
```

---

## Environment Configuration

Create local environment files from the provided templates:

```powershell
Copy-Item apps\api\.env.example apps\api\.env

Copy-Item infra\litellm\.env.example infra\litellm\.env
```

Replace all placeholder values locally.

Example LiteLLM configuration:

```env
LITELLM_MASTER_KEY=replace-me

LITELLM_SALT_KEY=

POSTGRES_PASSWORD=replace-me

UI_USERNAME=

LOCAL_VLLM_HOST=replace-me
```

Real `.env` files must never be committed.

---

## Python Environment

Create the FastAPI virtual environment:

```powershell
cd D:\AI\llm-deployment-lab\apps\api

python -m venv .venv
```

Upgrade pip:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Install project dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For reproduction using the locked dependency set:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```

---

## Database Migrations

Start PostgreSQL first, then run:

```powershell
cd D:\AI\llm-deployment-lab\apps\api

.\.venv\Scripts\python.exe -m alembic upgrade head
```

Current application tables:

```text
users

conversations

messages

model_calls
```

---

## Start the Platform

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-platform.ps1
```

The startup script is designed to start only missing local services rather than blindly duplicating already occupied ports.

---

## Main URLs

### Web Application

```text
http://127.0.0.1:5500
```

### FastAPI

```text
http://127.0.0.1:8002
```

### FastAPI Documentation

```text
http://127.0.0.1:8002/docs
```

### Usage Dashboard

```text
http://127.0.0.1:5500/usage.html
```

### LiteLLM Gateway

```text
http://127.0.0.1:4000
```

---

## Health Check

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\health-check.ps1
```

The script checks important local ports and HTTP health endpoints.

---

## Stop the Platform

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop-platform.ps1
```

The stop process preserves PostgreSQL volumes.

Application data therefore remains available after service shutdown and restart.

---

## API Overview

Detailed API documentation:

[`docs/API.md`](docs/API.md)

Core endpoints currently include:

### Authentication

```text
POST /auth/register

POST /auth/login

GET /auth/me
```

### Models

```text
GET /models
```

### Chat

```text
POST /chat

POST /chat/stream
```

### Conversations

```text
GET /conversations

POST /conversations

GET /conversations/{conversation_id}

PATCH /conversations/{conversation_id}

DELETE /conversations/{conversation_id}
```

### Messages

```text
GET /conversations/{conversation_id}/messages
```

### Model Calls

```text
GET /model-calls

GET /model-calls/summary
```

### Health

```text
GET /health

GET /health/readiness
```

---

## Engineering Challenges Solved

The project involved several practical engineering problems beyond simple API integration.

### 1. Multi-Provider API Differences

Problem:

```text
Different Providers
       |
       v
Different APIs
       |
       v
Application Complexity
```

Solution:

```text
LiteLLM Gateway
```

provides a common model access layer.

---

### 2. Cloud and Local Models Use Different Infrastructure

Cloud models are accessed through external APIs.

The local model runs on a private Linux GPU server.

The unified architecture solves this through:

```text
FastAPI
   |
   v
LiteLLM
   |
   +--> Cloud API
   |
   +--> Local vLLM API
```

---

### 3. Model Weights Are Not a Serving API

After downloading Qwen2.5-7B-Instruct, the model still needed to be converted into an accessible service.

vLLM was introduced to provide:

```text
Model Weights
      |
      v
    vLLM
      |
      v
HTTP Model Service
```

---

### 4. Windows and Linux Could Not Communicate Directly

The development machine and GPU server were located on different networks.

Tailscale was used to create private cross-host connectivity.

---

### 5. Docker Proxy Routing Broke Cloud Requests

During development, a failure of the local direct proxy caused multiple cloud models to fail simultaneously while the local model remained available.

This helped isolate the architecture into two different network paths:

```text
Cloud Models
   |
   v
Proxy
```

versus:

```text
Local Model
   |
   v
Tailscale
```

---

### 6. Proxy Routing Interfered with Local Model Traffic

The LiteLLM container used HTTP proxy settings for cloud providers.

The local Tailscale address needed to bypass the proxy.

The solution used:

```text
NO_PROXY
```

to keep local model traffic on the private route.

---

### 7. LiteLLM Virtual Key Initially Rejected the Local Model

The FastAPI application key originally allowed only the existing cloud models.

After introducing:

```text
qwen2.5-7b-local
```

LiteLLM returned a model access denial.

The restricted key configuration was updated to explicitly include the local model.

---

### 8. GPU Memory Constraints

Deploying Qwen2.5-7B required consideration of:

- model weight size
- available VRAM
- KV cache
- maximum context length
- model-serving overhead

The final stable serving configuration successfully ran Qwen2.5-7B-Instruct on an RTX 3090.

---

### 9. Multiple Local Services Created Port Conflicts

The platform uses several independent services:

```text
Web

FastAPI

LiteLLM

PostgreSQL

Direct Proxy

vLLM
```

Fixed ports, startup scripts, and health-check scripts were introduced to reduce accidental duplicate processes.

---

### 10. Runtime Configuration Should Not Be Hard-Coded

Sensitive and environment-specific values such as:

- API keys
- passwords
- server addresses
- LiteLLM keys

are stored in local environment files rather than committed into source code.

---

## SGLang Evaluation

After the vLLM serving path was verified, SGLang was evaluated as a possible alternative local inference engine.

The planned comparison included:

- time to first token
- total response latency
- token throughput
- GPU memory usage
- concurrency behavior

A separate Conda environment was created to avoid modifying the stable vLLM environment.

A CUDA 11.8-oriented compatibility stack was investigated using combinations around:

```text
Python 3.10

PyTorch 2.4

SGLang 0.3.x
```

However, the available GPU servers were shared research machines running older system stacks such as:

```text
Ubuntu 18.04

Legacy NVIDIA drivers

CUDA 11.x
```

The legacy SGLang dependency chain introduced compatibility issues involving:

- historical vLLM dependencies
- pyarrow wheels
- source builds
- Rust build dependencies
- CUDA compatibility
- kernel compatibility

The shared servers also contained active workloads from other users.

Upgrading:

- the operating system
- NVIDIA drivers
- global CUDA installation

or rebooting the server would have risked interrupting unrelated GPU workloads.

For this reason, the project intentionally keeps:

```text
vLLM
```

as the verified stable local serving backend.

SGLang remains a future benchmark target for a modern isolated GPU environment.

---

## Why the SGLang Limitation Is Not a GPU Capacity Issue

The local RTX 3090 successfully runs:

```text
Qwen2.5-7B-Instruct
```

through vLLM.

Therefore, the SGLang limitation is primarily related to:

```text
Legacy System Stack
        +
Dependency Compatibility
        +
Shared Server Constraints
```

rather than insufficient GPU compute capability.

---

## Security

The project follows several basic security practices.

### Environment Isolation

Real API keys and passwords are stored in `.env` files.

Only `.env.example` templates are committed.

---

### Restricted LiteLLM Access

FastAPI uses a restricted LiteLLM Virtual Key rather than the administrative master key for normal model requests.

---

### User Data Isolation

Conversation and model-call data are associated with authenticated users.

---

### Repository Secret Scan

Before pushing changes:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\security-scan.ps1
```

The repository-level `.gitignore` excludes:

- `.env`
- virtual environments
- backups
- caches
- local runtime files

Always review:

```powershell
git status
```

before pushing.

---

## Git Workflow

The project uses Git for source-version management.

Typical workflow:

```text
Modify Files
    |
    v
git add
    |
    v
Staging Area
    |
    v
git commit
    |
    v
Local Revision
    |
    v
git push
    |
    v
GitHub
```

This keeps major project changes traceable and reversible.

---

## Technology Stack

### Application Backend

- Python
- FastAPI
- Pydantic
- JWT

### Persistence

- PostgreSQL
- SQLAlchemy
- Alembic

### Model Gateway

- LiteLLM

### Local Model Serving

- Qwen2.5-7B-Instruct
- vLLM
- PyTorch
- CUDA
- Linux
- NVIDIA RTX 3090

### Cloud Model Providers

- Alibaba Cloud Bailian / Qwen
- DeepSeek

### Infrastructure

- Docker
- Docker Compose

### Networking

- Tailscale
- HTTP Proxy
- NO_PROXY configuration

### Frontend

- HTML
- CSS
- JavaScript

### Engineering Tooling

- Git
- GitHub
- PowerShell
- Environment Variables
- Health-check scripts
- Security scan scripts

---

## Verified End-to-End Paths

### Cloud Model

```text
Web
 |
 v
FastAPI
 |
 v
LiteLLM
 |
 v
Cloud Provider API
 |
 v
Model Response
 |
 v
FastAPI
 |
 v
PostgreSQL
 |
 v
Web
```

### Local Model

```text
Web
 |
 v
FastAPI
 |
 v
LiteLLM
 |
 v
Tailscale
 |
 v
Linux
 |
 v
vLLM
 |
 v
Qwen2.5-7B-Instruct
 |
 v
RTX 3090
 |
 v
Model Response
 |
 v
FastAPI
 |
 v
PostgreSQL
 |
 v
Web
```

---

## Future Work

### Serving

- vLLM vs SGLang benchmark
- time-to-first-token measurement
- generation throughput measurement
- concurrency testing
- GPU memory monitoring
- dynamic model loading

### Gateway

- automatic fallback
- retry policies
- load balancing
- health-aware routing
- circuit breaking

### Access Control

- RBAC
- administrator roles
- user quotas
- model-level quotas

### Cost Management

- provider cost accounting
- per-user token budget
- model cost comparison
- usage-based reporting

### Observability

- structured logging
- Prometheus metrics
- Grafana dashboards
- alerting
- provider SLA tracking

### Platform Engineering

- Redis caching
- automated testing
- CI/CD
- containerized FastAPI deployment
- production reverse proxy
- production deployment

---

## Resume Material

A concise Chinese resume description and interview talking points are available in:

[`docs/RESUME_PROJECT.md`](docs/RESUME_PROJECT.md)

---

## Project Summary

The project implements a complete LLM application path from the browser to both cloud and self-hosted models:

```text
Frontend
   |
   v
FastAPI
   |
   v
LiteLLM
   |
   +-------------------+
   |                   |
   v                   v
Cloud APIs          Local vLLM
                        |
                        v
                    Qwen2.5-7B
                        |
                        v
                     RTX 3090
```

The platform currently combines:

- multi-provider model integration
- cloud model APIs
- self-hosted model serving
- GPU inference
- unified model routing
- authentication
- conversation persistence
- database migrations
- token and latency observability
- Docker infrastructure
- private cross-host networking
- proxy routing
- model access control
- environment isolation
- Git-based version management

The current stable release demonstrates that cloud APIs and self-hosted open-weight models can be exposed through the same application interface while keeping the business layer, model gateway, and inference-serving layer cleanly separated.