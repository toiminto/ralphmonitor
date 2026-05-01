# Technology Stack Research

## Recommendation: Python + FastAPI + Vanilla JS

### Backend: Python 3.12+ with FastAPI
- **Why**: Excellent async HTTP handling, built-in OpenAPI docs, lightweight
- **HTTP proxy**: `httpx` for async request forwarding to llama.cpp
- **GPU monitoring**: `pynvml` (NVIDIA Management Library) for GPU stats
- **System monitoring**: `psutil` for CPU/memory
- **Database**: `sqlite3` (built-in) with WAL mode for concurrent access
- **Real-time**: WebSocket support built into FastAPI for live dashboard updates
- **Scheduling**: `APScheduler` or `asyncio` tasks for periodic GPU/system polling

### Frontend: Vanilla HTML/CSS/JS (no build step)
- **Why**: Minimal Docker image, no Node.js build step, served as static files
- **Charting**: ApexCharts.js — modern, interactive, good real-time support, free
- **Real-time updates**: WebSocket connection for live data push
- **Responsive**: CSS Grid/Flexbox, mobile-friendly
- **Served by**: FastAPI `StaticFiles`

### Alternative Considered
- **Node.js**: Larger ecosystem but heavier Docker image, less natural for GPU monitoring
- **Go**: Smallest image but more verbose, less ecosystem for data viz
- **React/Vue**: Overkill for this scope, requires build step in Docker

## Docker Strategy
- **Base image**: `python:3.12-slim` (~150MB)
- **NVIDIA runtime**: Use `--gpus all` flag at runtime for GPU access
- **Multi-stage**: Not needed (single stage is sufficient for Python)
- **Volume mounts**: SQLite DB on volume for persistence
- **Health check**: HTTP probe on `/health` endpoint
- **Target image size**: ~200-250MB

## SQLite Schema Considerations
- WAL mode for concurrent reads/writes
- Indexed by timestamp for range queries
- Periodic cleanup (DELETE older than retention period)
- Vacuum on schedule to reclaim space
