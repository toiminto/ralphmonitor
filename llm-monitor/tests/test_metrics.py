"""Tests for metric extraction."""

import pytest
from src.metrics import extract_non_streaming, extract_streaming


class TestExtractNonStreaming:
    def test_full_response(self):
        response = {
            "usage": {
                "prompt_tokens": 42,
                "completion_tokens": 128,
                "total_tokens": 170,
            },
            "timings": {
                "prompt_n": 42,
                "prompt_ms": 850.5,
                "predicted_n": 128,
                "predicted_ms": 2400.3,
            },
        }
        result = extract_non_streaming(response, 3250.0, 512, 2048)

        assert result["prompt_tokens"] == 42
        assert result["completion_tokens"] == 128
        assert result["total_tokens"] == 170
        assert result["prompt_ms"] == 850.5
        assert result["predicted_ms"] == 2400.3
        assert result["total_latency_ms"] == 3250.0
        assert result["time_to_first_token_ms"] is None
        assert result["request_body_size"] == 512
        assert result["response_body_size"] == 2048
        assert result["prompt_tokens_per_second"] == pytest.approx(49.38, rel=0.01)
        assert result["generation_tokens_per_second"] == pytest.approx(53.33, rel=0.01)

    def test_empty_response(self):
        result = extract_non_streaming({}, 100.0, 100, 200)
        assert result["prompt_tokens"] == 0
        assert result["completion_tokens"] == 0
        assert result["prompt_tokens_per_second"] is None
        assert result["generation_tokens_per_second"] is None

    def test_missing_timings(self):
        response = {"usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}
        result = extract_non_streaming(response, 50.0, 50, 100)
        assert result["prompt_tokens"] == 10
        assert result["prompt_ms"] is None
        assert result["prompt_tokens_per_second"] is None


class TestExtractStreaming:
    def test_full_chunk(self):
        chunk = {
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 8,
                "total_tokens": 23,
            },
            "timings": {
                "prompt_n": 15,
                "prompt_ms": 30.5,
                "predicted_n": 8,
                "predicted_ms": 240.0,
            },
        }
        result = extract_streaming(chunk, 320.0, 89.5, 256, 1024)

        assert result["prompt_tokens"] == 15
        assert result["completion_tokens"] == 8
        assert result["total_tokens"] == 23
        assert result["total_latency_ms"] == 320.0
        assert result["time_to_first_token_ms"] == 89.5
        assert result["prompt_tokens_per_second"] == pytest.approx(491.8, rel=0.01)
        assert result["generation_tokens_per_second"] == pytest.approx(33.33, rel=0.01)

    def test_empty_chunk(self):
        result = extract_streaming({}, 100.0, 50.0, 100, 200)
        assert result["prompt_tokens"] == 0
        assert result["time_to_first_token_ms"] == 50.0
