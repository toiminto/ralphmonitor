# LLM Performance Monitor

A Dockerized reverse proxy and monitoring dashboard for locally hosted llama.cpp servers.

Sits between your LLM clients and the llama.cpp server, intercepting all requests to collect per-request metrics (token speed, latency, usage) and system metrics (GPU, CPU, VRAM). Provides an interactive web dashboard with real-time and historical views.

## Quick Start

```bash
# Clone and build
git clone <repo>
cd llm-monitor
docker compose up -d --build

# Open dashboard
open http://localhost:8008/dashboard
```

Point your LLM clients at `http://localhost:8008` instead of `http://localhost:8080`.

## Architecture

```
Client → LLM Monitor :8008 → llama.cpp :8080
              │
              ├─ SQLite (metrics DB)
              ├─ GPU polling (pynvml)
              ├─ CPU polling (psutil)
              └─ WebSocket → Dashboard
```

## Configuration

All configuration via environment variables:

| Variable | Default | Description |
|---|---|---|
| `LLM_BACKEND_URL` | `http://localhost:8080` | llama.cpp server address |
| `MONITOR_PORT` | `8008` | Monitor port |
| `DB_PATH` | `/data/metrics.db` | SQLite database path |
| `RETENTION_DAYS` | `30` | Days to keep historical data |
| `GPU_POLL_INTERVAL` | `5` | Seconds between GPU polls |
| `CPU_POLL_INTERVAL` | `10` | Seconds between CPU polls |
| `CLEANUP_INTERVAL` | `3600` | Seconds between retention cleanups |

### Docker Run

```bash
docker run -d \
  --name llm-monitor \
  --gpus all \
  -p 8008:8008 \
  -v llm-monitor-data:/data \
  -e LLM_BACKEND_URL=http://host.docker.internal:8080 \
  llm-monitor:latest
```

### Docker Compose

```yaml
services:
  llm-monitor:
    build: .
    ports:
      - "8008:8008"
    volumes:
      - llm-monitor-data:/data
    environment:
      - LLM_BACKEND_URL=http://host.docker.internal:8080
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/v1/*` | Any | Proxied to llama.cpp |
| `/health` | GET | Health check |
| `/dashboard` | GET | Web dashboard |
| `/api/metrics/requests` | GET | Request metrics |
| `/api/metrics/system` | GET | System metrics |
| `/api/metrics/summary` | GET | Aggregate stats |
| `/api/metrics/models` | GET | Known models |
| `/ws` | WS | Real-time updates |

## Dashboard Features

- **Summary cards**: Requests, latency, tokens, success rate, GPU/CPU usage
- **Token speed chart**: Prompt TPS and generation TPS over time
- **Utilization chart**: GPU%, CPU%, VRAM% over time
- **Token usage chart**: Prompt vs completion tokens
- **Latency chart**: End-to-end latency over time
- **Request table**: Sortable, filterable recent requests
- **Date range picker**: Today, 7 days, 30 days, custom range
- **Model filter**: Filter by model name
- **Real-time updates**: WebSocket push with auto-reconnect
- **Dark theme**: Easy on the eyes

## Troubleshooting

### GPU monitoring not working
- Ensure `--gpus all` is passed to Docker
- Check that NVIDIA drivers are installed on the host
- GPU polling gracefully degrades if no GPU is detected

### llama.cpp unreachable
- Verify `LLM_BACKEND_URL` points to the correct address
- In Docker with port mapping, use `host.docker.internal` instead of `localhost`
- Check `/health` endpoint for backend status

### Data not persisting
- Ensure the `/data` volume is mounted correctly
- SQLite database is stored at `DB_PATH` (default: `/data/metrics.db`)

## Tech Stack

- **Backend**: Python 3.12, FastAPI, httpx, uvicorn
- **GPU**: pynvml (NVIDIA), psutil (CPU/memory)
- **Database**: SQLite with WAL mode
- **Frontend**: Vanilla HTML/CSS/JS, ApexCharts.js
- **Real-time**: WebSocket (FastAPI native)
- **Container**: Docker, python:3.12-slim base image
