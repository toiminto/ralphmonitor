"""Reverse proxy handler for llama.cpp requests."""

import asyncio
import logging
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

from src.config import Config
from src.metrics import extract_non_streaming, extract_streaming
from src.storage import store_request_metric, store_error_metric
from src.websocket import broadcaster

logger = logging.getLogger(__name__)

proxy_router = APIRouter()

# Shared async client with connection pooling
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(300.0, connect=10.0),
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
)


@proxy_router.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(request: Request, path: str):
    """Forward requests to llama.cpp and collect metrics."""
    backend_url = f"{Config.LLM_BACKEND_URL}/v1/{path}"
    start_time = time.monotonic()

    # Read request body
    body = await request.body()

    # Extract model and stream flag from request body
    model = None
    is_stream = False
    try:
        import json
        body_dict = json.loads(body) if body else {}
        model = body_dict.get("model")
        is_stream = body_dict.get("stream", False)
    except (json.JSONDecodeError, AttributeError):
        pass

    # Build headers (pass through relevant ones)
    headers = {}
    for key, value in request.headers.items():
        if key not in ("host", "connection", "content-length"):
            headers[key] = value

    logger.info(f"Proxying {request.method} /v1/{path} (model={model}, stream={is_stream}) → {backend_url}")

    try:
        # Forward request to backend
        backend_response = await http_client.send(
            httpx.Request(
                method=request.method,
                url=backend_url,
                headers=headers,
                content=body,
            ),
            stream=True,
        )
    except (httpx.ConnectError, httpx.ConnectTimeout):
        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.error(f"llama.cpp unreachable: {backend_url}")
        _store_error_metric(model, path, elapsed_ms, "Backend unreachable")
        return JSONResponse(
            status_code=502,
            content={"error": "llama.cpp backend is unreachable"},
        )
    except Exception as e:
        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.error(f"Proxy error: {e}")
        _store_error_metric(model, path, elapsed_ms, str(e))
        return JSONResponse(
            status_code=502,
            content={"error": f"Proxy error: {str(e)}"},
        )

    # Detect streaming from response headers or request flag
    content_type = backend_response.headers.get("content-type", "")
    is_actual_stream = is_stream or "text/event-stream" in content_type

    if is_actual_stream:
        return await _handle_streaming_response(
            backend_response, path, model, start_time, body
        )

    return await _handle_non_streaming_response(
        backend_response, path, model, start_time, body
    )


async def _handle_non_streaming_response(backend_response, path, model, start_time, request_body):
    """Handle non-streaming JSON response."""
    try:
        response_body = await backend_response.aread()
        response_json = backend_response.json()
    except Exception as e:
        logger.warning(f"Failed to parse backend response: {e}")
        response_body = backend_response._content or b""
        response_json = {}

    elapsed_ms = (time.monotonic() - start_time) * 1000
    response_size = len(response_body)

    # Extract metrics
    if backend_response.status_code == 200:
        metrics = extract_non_streaming(
            response_json,
            elapsed_ms,
            len(request_body),
            response_size,
        )
        # Store async — never block the client
        asyncio.create_task(
            _safe_store_metric(
                path,
                model,
                backend_response.status_code,
                metrics,
            )
        )

    logger.info(f"Completed /v1/{path}: status={backend_response.status_code}, latency={elapsed_ms:.0f}ms, model={model}")

    # Build response for client
    return JSONResponse(
        content=response_json,
        status_code=backend_response.status_code,
        headers=dict(backend_response.headers),
    )


async def _handle_streaming_response(backend_response, path, model, start_time, request_body):
    """Handle streaming SSE response."""
    first_token_time: Optional[float] = None
    all_chunks = []
    total_response_size = 0

    async def stream_to_client():
        nonlocal first_token_time, total_response_size
        async for chunk in backend_response.aiter_bytes():
            if first_token_time is None:
                first_token_time = time.monotonic()
            total_response_size += len(chunk)
            all_chunks.append(chunk)
            yield chunk

        # Streaming is complete — extract and store metrics now
        await _extract_streaming_metrics(
            first_token_time, start_time, all_chunks, total_response_size,
            len(request_body), path, model, backend_response.status_code,
        )

    # Create streaming response
    response = StreamingResponse(
        stream_to_client(),
        status_code=backend_response.status_code,
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

    return response


async def _extract_streaming_metrics(first_token_time, start_time, all_chunks, total_response_size, request_body_size, path, model, status_code):
    """Extract metrics from completed streaming response."""
    elapsed_ms = (time.monotonic() - start_time) * 1000
    ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else None

    # Parse final chunks for usage/timings
    last_chunk_json = None
    try:
        combined = b"".join(all_chunks)
        text = combined.decode("utf-8", errors="replace")
        for line in reversed(text.split("\n")):
            line = line.strip()
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    import json
                    last_chunk_json = json.loads(line[6:])
                    break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning(f"Failed to parse streaming chunks: {e}")

    if last_chunk_json:
        metrics = extract_streaming(
            last_chunk_json,
            elapsed_ms,
            ttft_ms,
            request_body_size,
            total_response_size,
        )
        await _safe_store_metric(
            path,
            model,
            status_code,
            metrics,
        )
    else:
        logger.warning(f"No valid JSON found in streaming response for /v1/{path}")


async def _safe_store_metric(path, model, status_code, metrics):
    """Store metrics without blocking — errors are logged only."""
    try:
        record = {
            "endpoint": f"/v1/{path}",
            "model": model,
            "status_code": status_code,
            **metrics,
        }
        store_request_metric(record)
        # Broadcast to connected WebSocket clients
        await broadcaster.broadcast_request_metric(record)
    except Exception as e:
        logger.error(f"Failed to store metric: {e}")


def _store_error_metric(model, path, elapsed_ms, error_msg):
    """Store error metric synchronously (during error path)."""
    try:
        store_error_metric({
            "endpoint": f"/v1/{path}",
            "model": model,
            "status_code": 502,
            "error": error_msg,
            "total_latency_ms": elapsed_ms,
        })
    except Exception as e:
        logger.error(f"Failed to store error metric: {e}")
