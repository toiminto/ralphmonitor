# Implementation Plan: LLM Performance Monitor

## Overview

Numbered incremental steps to build the LLM monitor. Each step is independently testable and adds visible functionality. Core end-to-end proxy + dashboard is available by Step 4.

---

## Step 1: Project Skeleton and Docker Base

**Objective**: Set up the project structure, dependencies, and Dockerfile with a working health endpoint.

**Implementation:**
- Create project directory structure:
  ```
  llm-monitor/
  ├── Dockerfile
  ├── docker-compose.yml
  ├── requirements.txt
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
  ├── static/              # Frontend files
  │   ├── index.html
  │   ├── css/
  │   └── js/
  └── tests/
      ├── test_proxy.py
      ├── test_metrics.py
      ├── test_storage.py
      └── test_api.py
  ```
- Implement `config.py`: Load environment variables with defaults
- Implement `app.py`: FastAPI app with `/health` endpoint
- Write `Dockerfile`: python:3.12-slim base, install deps, expose 8080
- Write `docker-compose.yml`: GPU support, volume mount, env vars

**Test Requirements:**
- `docker build` succeeds
- `docker compose up` starts the container
- `curl localhost:8080/health` returns `{"status": "ok"}`

**Demo**: Container starts, health endpoint responds.

---

## Step 2: Reverse Proxy Core

**Objective**: Transparently forward `/v1/*` requests to llama.cpp and return responses.

**Implementation:**
- Implement `proxy.py`:
  - `httpx.AsyncClient` with connection pooling
  - Catch-all route for `/v1/*`
  - Forward non-streaming requests (full body)
  - Forward streaming requests (SSE chunk-by-chunk)
  - Pass through request headers (auth, content-type, etc.)
  - Handle errors: 502 when llama.cpp is unreachable
- Implement basic metric capture (just log for now, storage in Step 3):
  - Record start/end timestamps
  - Parse response body for `usage` and `timings` fields

**Test Requirements:**
- Unit test: Mock llama.cpp response, verify proxy forwards correctly
- Unit test: Mock streaming response, verify SSE chunks forwarded
- Unit test: llama.cpp down → 502 response
- Integration: Send real request through proxy to llama.cpp, verify identical response

**Demo**: `curl -X POST http://localhost:8080/v1/chat/completions -d '{...}'` returns same result as calling llama.cpp directly on port 8000.

---

## Step 3: Metric Extraction and SQLite Storage

**Objective**: Extract metrics from responses and persist them in SQLite.

**Implementation:**
- Implement `metrics.py`:
  - `extract_non_streaming(response_json)` → dict of metrics
  - `extract_streaming(final_chunk)` → dict of metrics
  - Derive: prompt TPS, generation TPS, total latency, TTFT
- Implement `storage.py`:
  - `init_db()`: Create tables with schema from design
  - `store_request_metric(data)`: Insert into `requests` table
  - `store_system_metric(data)`: Insert into `system_metrics` table
  - `cleanup_old_records(days)`: DELETE + VACUUM
  - Query helpers: `get_requests(start, end, model)`, `get_system_metrics(start, end)`
  - WAL mode enabled, indexed queries
- Wire metric extraction into proxy handler
- Add error handling: storage failures never block proxy

**Test Requirements:**
- Unit test: Parse mock non-streaming response → correct metrics dict
- Unit test: Parse mock streaming final chunk → correct metrics dict
- Unit test: Store and query request metrics by date range
- Unit test: Cleanup deletes old records, keeps recent ones
- Integration: Send request through proxy → verify metric appears in DB

**Demo**: After sending a few LLM requests, query SQLite directly and see stored metrics with accurate timing data.

---

## Step 4: Dashboard REST API and Basic Web UI

**Objective**: Serve metrics data via REST API and display a working (basic) dashboard.

**Implementation:**
- Implement `api.py`:
  - `GET /api/metrics/requests?from=&to=&model=` — paginated request metrics
  - `GET /api/metrics/system?from=&to=` — system metrics time series
  - `GET /api/metrics/summary` — aggregate stats (total requests, avg latency, total tokens, etc.)
  - `GET /api/metrics/models` — proxy to llama.cpp `/props` for model info
- Implement `static/index.html`:
  - Basic layout with summary cards
  - ApexCharts line chart for token speed over time
  - ApexCharts line chart for GPU/CPU utilization
  - Auto-refresh every 10 seconds via REST API polling
- Wire API routes into FastAPI app
- Serve static files via `StaticFiles`

**Test Requirements:**
- Unit test: API returns correct JSON structure
- Unit test: Date filtering works correctly
- Integration: Dashboard loads at `/dashboard`, charts render with data

**Demo**: Open `http://localhost:8080/dashboard` → see live-updating charts with real metrics from LLM requests.

**This is the core end-to-end milestone.**

---

## Step 5: GPU and CPU System Pollers

**Objective**: Collect GPU and CPU metrics and display them on the dashboard.

**Implementation:**
- Implement `pollers.py`:
  - `GPUPoller`: Initialize pynvml, collect GPU utilization/memory/temp/power every 5s
  - `SystemPoller`: Use psutil for CPU/memory/swap every 10s
  - `RetentionCleaner`: Delete old records hourly
  - Graceful startup: if pynvml fails, log and skip GPU polling
  - All pollers run as `asyncio` background tasks
- Wire pollers into `app.py` startup/shutdown lifecycle events
- Add GPU/CPU chart to dashboard
- Add system metrics summary cards (current GPU%, VRAM usage, CPU%)

**Test Requirements:**
- Unit test: Mock pynvml, verify GPU metrics dict structure
- Unit test: Mock psutil, verify system metrics dict structure
- Unit test: Retention cleaner deletes old records
- Integration: Verify system_metrics table populated after startup
- Manual: Verify GPU metrics match `nvidia-smi` output

**Demo**: Dashboard shows real-time GPU utilization and VRAM usage that correlates with LLM inference load.

---

## Step 6: WebSocket Real-Time Updates

**Objective**: Replace polling with WebSocket push for real-time dashboard updates.

**Implementation:**
- Implement `websocket.py`:
  - `WebSocketBroadcaster`: Manage connected clients, broadcast messages
  - `WS /ws`: WebSocket endpoint with auto-reconnect support
  - Push `request_metric` events on each completed request
  - Push `system_metric` snapshots every 10 seconds
- Update `static/js/dashboard.js`:
  - Connect to WebSocket on page load
  - Update charts on received messages (no page refresh)
  - Auto-reconnect with exponential backoff
  - Fallback to REST polling if WebSocket unavailable
- Wire broadcaster into proxy handler and pollers

**Test Requirements:**
- Unit test: Broadcaster sends to all connected clients
- Unit test: Disconnected clients are removed from set
- Integration: Connect WebSocket client, send LLM request, verify real-time update

**Demo**: Open dashboard in two browser tabs → both update simultaneously when an LLM request completes.

---

## Step 7: Interactive Dashboard Polish

**Objective**: Add filtering, date pickers, drill-downs, and responsive design.

**Implementation:**
- Add date range picker (Today, 7 days, 30 days, Custom range)
- Add model filter dropdown (populate from known models)
- Add request table with sorting (by time, latency, tokens)
- Add hover tooltips on charts with detailed metrics
- Add "no data" placeholders for empty date ranges
- Responsive CSS for mobile/tablet view
- Dark theme styling
- Connection status indicator (WebSocket live ● / offline ○)

**Test Requirements:**
- Manual: Date range filtering returns correct data subsets
- Manual: Model filter works when multiple models are used
- Manual: Dashboard is usable on mobile viewport
- Manual: Charts update correctly after filter changes

**Demo**: Full interactive dashboard with date filtering, model selection, sortable request table, and real-time updates.

---

## Step 8: Docker Hardening and Documentation

**Objective**: Production-ready Docker packaging and user documentation.

**Implementation:**
- Optimize Dockerfile:
  - Use `.dockerignore`
  - Multi-stage if beneficial
  - Non-root user
  - Health check instruction
- Update `docker-compose.yml` with all configuration options
- Write `README.md`:
  - Quick start (docker compose up)
  - Configuration reference (all env vars)
  - Architecture overview
  - Troubleshooting guide
- Add `docker-compose.yml` examples for common setups

**Test Requirements:**
- Build produces clean image (< 300MB target)
- `docker compose up -d` works with default config
- Container survives restart with data preserved
- Health check passes

**Demo**: Fresh machine → `git clone` → `docker compose up` → dashboard working at `localhost:8080/dashboard`.

---

## Step 9: Integration Tests and Final Verification

**Objective**: End-to-end verification and test coverage.

**Implementation:**
- Write integration test suite:
  - Start monitor container + mock llama.cpp
  - Send various requests (streaming, non-streaming, errors)
  - Verify metrics in database
  - Verify dashboard API responses
  - Verify WebSocket updates
- Test with real llama.cpp instance:
  - Deploy on local machine alongside llama.cpp
  - Send real inference requests
  - Verify all metrics are accurate
  - Test concurrent requests
  - Test data persistence across restarts

**Test Requirements:**
- All unit tests pass
- Integration tests pass in CI
- Manual verification on real llama.cpp instance

**Demo**: Complete system running end-to-end with real LLM traffic, accurate metrics, and polished dashboard.

---

## Dependency Order

```
Step 1 (skeleton)
    ↓
Step 2 (proxy core)
    ↓
Step 3 (metrics + storage)
    ↓
Step 4 (API + basic dashboard)  ← Core end-to-end
    ↓
Step 5 (system pollers)
    ↓
Step 6 (WebSocket real-time)
    ↓
Step 7 (dashboard polish)
    ↓
Step 8 (Docker hardening)
    ↓
Step 9 (integration tests)
```
