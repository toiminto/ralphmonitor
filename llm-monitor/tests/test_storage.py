"""Tests for SQLite storage."""

import os
import tempfile
import pytest
from datetime import datetime, timedelta

from src import config
from src.storage import init_db, store_request_metric, store_system_metric, get_requests, get_system_metrics, get_summary, get_models, cleanup_old_records


@pytest.fixture(autouse=True)
def temp_db():
    """Use a temporary database for each test."""
    original_db = config.Config.DB_PATH
    tmp_path = tempfile.mktemp(suffix=".db")
    config.Config.DB_PATH = tmp_path
    init_db()
    yield tmp_path
    config.Config.DB_PATH = original_db
    if os.path.exists(tmp_path):
        os.remove(tmp_path)


class TestRequestStorage:
    def test_store_and_retrieve(self):
        store_request_metric({
            "endpoint": "/v1/chat/completions",
            "model": "llama-3.1-8b",
            "status_code": 200,
            "prompt_tokens": 42,
            "completion_tokens": 128,
            "total_tokens": 170,
            "prompt_ms": 850.5,
            "predicted_ms": 2400.3,
            "prompt_tokens_per_second": 49.38,
            "generation_tokens_per_second": 53.33,
            "total_latency_ms": 3250.0,
            "request_body_size": 512,
            "response_body_size": 2048,
        })

        requests = get_requests()
        assert len(requests) == 1
        r = requests[0]
        assert r["model"] == "llama-3.1-8b"
        assert r["status_code"] == 200
        assert r["prompt_tokens"] == 42
        assert r["completion_tokens"] == 128

    def test_filter_by_model(self):
        store_request_metric({
            "endpoint": "/v1/chat/completions",
            "model": "model-a",
            "status_code": 200,
        })
        store_request_metric({
            "endpoint": "/v1/chat/completions",
            "model": "model-b",
            "status_code": 200,
        })

        assert len(get_requests(model="model-a")) == 1
        assert len(get_requests(model="model-b")) == 1
        assert len(get_requests()) == 2

    def test_get_models(self):
        store_request_metric({"endpoint": "/v1/chat/completions", "model": "llama-3.1-8b", "status_code": 200})
        store_request_metric({"endpoint": "/v1/chat/completions", "model": "mistral-7b", "status_code": 200})
        store_request_metric({"endpoint": "/v1/chat/completions", "model": "llama-3.1-8b", "status_code": 200})

        models = get_models()
        assert set(models) == {"llama-3.1-8b", "mistral-7b"}

    def test_summary(self):
        store_request_metric({
            "endpoint": "/v1/chat/completions",
            "model": "test",
            "status_code": 200,
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "total_latency_ms": 1000.0,
            "prompt_tokens_per_second": 100.0,
            "generation_tokens_per_second": 50.0,
        })
        store_request_metric({
            "endpoint": "/v1/chat/completions",
            "model": "test",
            "status_code": 200,
            "prompt_tokens": 20,
            "completion_tokens": 40,
            "total_tokens": 60,
            "total_latency_ms": 2000.0,
            "prompt_tokens_per_second": 200.0,
            "generation_tokens_per_second": 100.0,
        })

        summary = get_summary()
        assert summary["total_requests"] == 2
        assert summary["total_prompt_tokens"] == 30
        assert summary["total_completion_tokens"] == 60
        assert summary["total_all_tokens"] == 90
        assert summary["avg_latency_ms"] == pytest.approx(1500.0)
        assert summary["success_rate"] == 100.0


class TestSystemStorage:
    def test_store_and_retrieve(self):
        store_system_metric({
            "gpu_utilization": 85.0,
            "gpu_memory_used_mb": 6000.0,
            "gpu_memory_total_mb": 8192.0,
            "gpu_temperature": 72.0,
            "gpu_power_watts": 250.0,
            "cpu_usage": 45.0,
            "memory_used_mb": 4096.0,
            "memory_total_mb": 16384.0,
            "swap_used_mb": 0.0,
            "swap_total_mb": 8192.0,
        })

        metrics = get_system_metrics()
        assert len(metrics) == 1
        assert metrics[0]["gpu_utilization"] == 85.0
        assert metrics[0]["cpu_usage"] == 45.0


class TestRetention:
    def test_cleanup(self):
        # Store a recent record
        store_request_metric({
            "endpoint": "/v1/chat/completions",
            "model": "test",
            "status_code": 200,
        })
        assert len(get_requests()) == 1

        # Cleanup with 0 days should delete everything
        deleted = cleanup_old_records(0)
        assert deleted >= 1
        assert len(get_requests()) == 0
