# Summary: LLM Performance Monitor

## Artifacts

| File | Description |
|---|---|
| `specs/llm-monitor/rough-idea.md` | Original project idea |
| `specs/llm-monitor/requirements.md` | 8 Q&A items covering backend, architecture, metrics, retention, stack, UI, system access, auth |
| `specs/llm-monitor/design.md` | Complete design: architecture, components, data models, error handling, acceptance criteria, testing strategy |
| `specs/llm-monitor/plan.md` | 9-step implementation plan with objectives, tests, and demos per step |
| `specs/llm-monitor/research/llama-cpp-api.md` | llama.cpp API endpoints, timing fields, streaming behavior |
| `specs/llm-monitor/research/tech-stack.md` | Python/FastAPI + ApexCharts + SQLite + Docker strategy |
| `specs/llm-monitor/research/gpu-monitoring.md` | pynvml GPU monitoring, psutil system monitoring, Docker GPU access |
| `specs/llm-monitor/research/proxy-architecture.md` | Async reverse proxy design, streaming handling, error handling |

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| LLM Backend | llama.cpp server | User's existing setup |
| Architecture | Reverse proxy | Most accurate per-request metrics |
| Language | Python 3.12 | Natural fit for GPU monitoring + web dev |
| Web Framework | FastAPI | Async, lightweight, WebSocket support |
| Database | SQLite | Simple, persistent, sufficient for 100-1000 req/day |
| Charts | ApexCharts.js | Interactive, real-time, no build step |
| GPU Monitoring | pynvml | Direct NVML access, no shell overhead |
| System Monitoring | psutil | Cross-platform, lightweight |
| Real-time | WebSocket | Push-based, instant updates |
| Auth | None | Local trusted network |

## Next Steps

1. **Implement** — Follow the 9 steps in `plan.md`
2. **Deploy** — `docker compose up` on the LLM host machine
3. **Configure** — Point your LLM clients at `http://localhost:8080` instead of `http://localhost:8000`
4. **Monitor** — Open `http://localhost:8080/dashboard` for real-time stats
