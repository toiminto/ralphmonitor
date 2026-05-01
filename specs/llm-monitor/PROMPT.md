# PROMPT: LLM Performance Monitor — Spec-Driven Implementation

## Role

You are implementing the LLM Performance Monitor as specified in the design documents. Follow the implementation plan step by step, writing tests before code (TDD), and verify each step works before proceeding.

## Context

A Dockerized reverse proxy and monitoring dashboard for a locally hosted llama.cpp server. It sits between LLM clients and the llama.cpp server, intercepting all requests to collect per-request metrics and system metrics. An interactive web dashboard provides real-time and historical views.

## Specification Documents

Read these files for the complete specification:

- **Design**: `specs/llm-monitor/design.md` — Architecture, components, data models, acceptance criteria
- **Plan**: `specs/llm-monitor/plan.md` — 9-step implementation plan (follow this order)
- **Research**: `specs/llm-monitor/research/` — API details, tech choices, monitoring approach

## Implementation Rules

1. **Follow the plan**: Implement steps 1-9 in order from `plan.md`. Each step must be complete and tested before moving to the next.
2. **TDD**: Write tests before implementation code. Tests must pass before considering a step done.
3. **Match the design**: Use the exact SQLite schema, WebSocket message format, and API endpoints from `design.md`.
4. **Environment config**: All configuration via environment variables as specified in the design.
5. **Docker-first**: Everything must work inside the Docker container. Test with `docker compose up`.
6. **Error resilience**: Metric storage failures must never block client proxy requests.

## Tech Stack (Fixed)

- **Backend**: Python 3.12, FastAPI, httpx (async HTTP), uvicorn
- **GPU**: pynvml (NVIDIA), psutil (CPU/memory)
- **Database**: SQLite with WAL mode
- **Frontend**: Vanilla HTML/CSS/JS, ApexCharts.js (CDN)
- **Real-time**: WebSocket (FastAPI native)
- **Container**: Docker, python:3.12-slim base image

## Project Structure

```
llm-monitor/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── README.md
├── src/
│   ├── __init__.py
│   ├── app.py           # FastAPI app entry point
│   ├── config.py        # Environment config
│   ├── proxy.py         # Proxy handler
│   ├── metrics.py       # Metric extraction
│   ├── storage.py       # SQLite operations
│   ├── pollers.py       # GPU/CPU system pollers
│   ├── websocket.py     # WebSocket broadcaster
│   └── api.py           # Dashboard REST API
├── static/
│   ├── index.html
│   ├── css/
│   │   └── dashboard.css
│   └── js/
│       └── dashboard.js
└── tests/
    ├── test_proxy.py
    ├── test_metrics.py
    ├── test_storage.py
    ├── test_pollers.py
    ├── test_websocket.py
    └── test_api.py
```

## Step-by-Step Guide

### Step 1: Project Skeleton and Docker Base
- Create directory structure and all files
- Implement `config.py` with environment variable loading
- Implement `app.py` with FastAPI app and `/health` endpoint
- Write Dockerfile and docker-compose.yml with GPU support
- **Verify**: `docker compose up` starts, `curl localhost:8080/health` returns OK

### Step 2: Reverse Proxy Core
- Implement `proxy.py` with httpx.AsyncClient forwarding
- Handle non-streaming and streaming (SSE) responses
- Pass through headers, handle 502 errors
- **Verify**: Requests to `:8080/v1/*` reach llama.cpp on `:8000` and return identical responses

### Step 3: Metric Extraction and SQLite Storage
- Implement `metrics.py` for parsing llama.cpp response timing/token fields
- Implement `storage.py` with SQLite schema from design.md
- Wire extraction into proxy handler
- **Verify**: After requests, metrics appear in SQLite with correct values

### Step 4: Dashboard REST API and Basic Web UI
- Implement `api.py` with `/api/metrics/*` endpoints
- Create `static/index.html` with ApexCharts and summary cards
- **Verify**: Dashboard loads at `/dashboard`, shows real data from requests

### Step 5: GPU and CPU System Pollers
- Implement `pollers.py` with pynvml GPU polling and psutil system polling
- Wire into app lifecycle (startup/shutdown)
- Add GPU/CPU charts to dashboard
- **Verify**: Dashboard shows GPU utilization matching nvidia-smi

### Step 6: WebSocket Real-Time Updates
- Implement `websocket.py` broadcaster
- Update frontend to use WebSocket with REST fallback
- **Verify**: Dashboard updates in real-time without page refresh

### Step 7: Interactive Dashboard Polish
- Date range picker, model filter, sortable request table
- Responsive CSS, dark theme, connection status indicator
- **Verify**: All filters work, dashboard is mobile-friendly

### Step 8: Docker Hardening and Documentation
- Optimize Dockerfile (non-root user, health check, .dockerignore)
- Write README.md with quick start and configuration reference
- **Verify**: Clean build, fresh `docker compose up` works end-to-end

### Step 9: Integration Tests and Final Verification
- Write integration test suite with mock llama.cpp
- Test with real llama.cpp instance
- **Verify**: All tests pass, system works with real LLM traffic

## Key Design Details

### SQLite Schema (from design.md)
```sql
CREATE TABLE requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    endpoint TEXT NOT NULL,
    model TEXT,
    status_code INTEGER,
    error TEXT,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    prompt_ms REAL,
    predicted_ms REAL,
    prompt_tokens_per_second REAL,
    generation_tokens_per_second REAL,
    total_latency_ms REAL,
    time_to_first_token_ms REAL,
    request_body_size INTEGER,
    response_body_size INTEGER
);

CREATE TABLE system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    gpu_utilization REAL,
    gpu_memory_used_mb REAL,
    gpu_memory_total_mb REAL,
    gpu_temperature REAL,
    gpu_power_watts REAL,
    cpu_usage REAL,
    memory_used_mb REAL,
    memory_total_mb REAL,
    swap_used_mb REAL,
    swap_total_mb REAL
);
```

### Environment Variables
| Variable | Default | Description |
|---|---|---|
| `LLM_BACKEND_URL` | `http://localhost:8000` | llama.cpp server address |
| `MONITOR_PORT` | `8080` | Monitor port |
| `DB_PATH` | `/data/metrics.db` | SQLite path |
| `RETENTION_DAYS` | `30` | Data retention |
| `GPU_POLL_INTERVAL` | `5` | GPU poll seconds |
| `CPU_POLL_INTERVAL` | `10` | CPU poll seconds |
| `CLEANUP_INTERVAL` | `3600` | Cleanup seconds |

### llama.cpp Timing Fields
- `prompt_ms`, `prompt_n` → prompt processing time and token count
- `predicted_ms`, `predicted_n` → generation time and token count
- `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`

## Acceptance Criteria

All acceptance criteria from `design.md` must be satisfied. Key ones:
- Proxy forwards requests transparently (streaming + non-streaming)
- Metrics are accurately extracted and stored
- Dashboard shows real-time GPU/CPU/request metrics
- Data persists across container restarts
- Docker image builds and runs with `--gpus all`
