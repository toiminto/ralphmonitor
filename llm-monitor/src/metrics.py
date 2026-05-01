"""Metric extraction from llama.cpp responses."""

import logging

logger = logging.getLogger(__name__)


def extract_non_streaming(response_json: dict, total_latency_ms: float, request_body_size: int, response_body_size: int) -> dict:
    """Extract metrics from a non-streaming llama.cpp response."""
    metrics = {
        "total_latency_ms": total_latency_ms,
        "time_to_first_token_ms": None,
        "request_body_size": request_body_size,
        "response_body_size": response_body_size,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "prompt_ms": None,
        "predicted_ms": None,
        "prompt_tokens_per_second": None,
        "generation_tokens_per_second": None,
    }

    # Extract usage tokens
    usage = response_json.get("usage", {})
    if usage:
        metrics["prompt_tokens"] = usage.get("prompt_tokens", 0) or 0
        metrics["completion_tokens"] = usage.get("completion_tokens", 0) or 0
        metrics["total_tokens"] = usage.get("total_tokens", 0) or 0

    # Extract timings
    timings = response_json.get("timings", {})
    if timings:
        prompt_ms = timings.get("prompt_ms")
        predicted_ms = timings.get("predicted_ms")
        prompt_n = timings.get("prompt_n", 0) or 0
        predicted_n = timings.get("predicted_n", 0) or 0

        metrics["prompt_ms"] = prompt_ms
        metrics["predicted_ms"] = predicted_ms

        if prompt_ms and prompt_ms > 0 and prompt_n:
            metrics["prompt_tokens_per_second"] = round(prompt_n / (prompt_ms / 1000), 2)
        if predicted_ms and predicted_ms > 0 and predicted_n:
            metrics["generation_tokens_per_second"] = round(predicted_n / (predicted_ms / 1000), 2)

    return metrics


def extract_streaming(final_chunk: dict, total_latency_ms: float, ttft_ms: float, request_body_size: int, response_body_size: int) -> dict:
    """Extract metrics from the final SSE chunk of a streaming response."""
    metrics = {
        "total_latency_ms": total_latency_ms,
        "time_to_first_token_ms": ttft_ms,
        "request_body_size": request_body_size,
        "response_body_size": response_body_size,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "prompt_ms": None,
        "predicted_ms": None,
        "prompt_tokens_per_second": None,
        "generation_tokens_per_second": None,
    }

    # Extract usage tokens
    usage = final_chunk.get("usage", {})
    if usage:
        metrics["prompt_tokens"] = usage.get("prompt_tokens", 0) or 0
        metrics["completion_tokens"] = usage.get("completion_tokens", 0) or 0
        metrics["total_tokens"] = usage.get("total_tokens", 0) or 0

    # Extract timings
    timings = final_chunk.get("timings", {})
    if timings:
        prompt_ms = timings.get("prompt_ms")
        predicted_ms = timings.get("predicted_ms")
        prompt_n = timings.get("prompt_n", 0) or 0
        predicted_n = timings.get("predicted_n", 0) or 0

        metrics["prompt_ms"] = prompt_ms
        metrics["predicted_ms"] = predicted_ms

        if prompt_ms and prompt_ms > 0 and prompt_n:
            metrics["prompt_tokens_per_second"] = round(prompt_n / (prompt_ms / 1000), 2)
        if predicted_ms and predicted_ms > 0 and predicted_n:
            metrics["generation_tokens_per_second"] = round(predicted_n / (predicted_ms / 1000), 2)

    return metrics
