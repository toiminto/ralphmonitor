# Proxy Architecture Research

## Design: Async Reverse Proxy with FastAPI

### Request Flow
```
Client → Monitor (port 8080) → llama.cpp (localhost:8000)
         ↓
    Extract metrics
         ↓
    Store in SQLite
         ↓
    Push to WebSocket clients
```

### Implementation Approach

1. **FastAPI as proxy**: Catch-all route for `/v1/*` endpoints
2. **httpx.AsyncClient**: Forward requests to llama.cpp with streaming support
3. **Response parsing**:
   - Non-streaming: Parse full JSON response for timing/token fields
   - Streaming (SSE): Parse final SSE chunk for timing data, proxy all chunks to client
4. **Metric extraction middleware**: Decorator or middleware pattern

### Streaming Response Handling
- Read SSE chunks from llama.cpp
- Forward each chunk to client via streaming response
- Parse the last chunk (contains `usage` and `timings` fields)
- Store extracted metrics after response completes

### Error Handling
- If llama.cpp is down, return 502 with helpful message
- Log failed requests with error details
- Never block the client on metric storage failures

### Concurrent Request Support
- FastAPI async handles concurrent requests naturally
- SQLite WAL mode supports concurrent reads
- Write queue or async lock for metric storage

### Key Endpoints Exposed by Monitor
- `/v1/*` — Proxied to llama.cpp
- `/health` — Monitor health + llama.cpp health
- `/dashboard` — Web UI
- `/api/metrics/*` — REST API for dashboard data
- `/ws` — WebSocket for real-time updates
