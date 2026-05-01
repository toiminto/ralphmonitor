"""SQLite storage for metrics data."""

import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta

from src.config import Config

logger = logging.getLogger(__name__)


def _get_connection():
    """Get a thread-safe database connection."""
    db_dir = os.path.dirname(Config.DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(Config.DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables and indexes."""
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS requests (
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

            CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp);
            CREATE INDEX IF NOT EXISTS idx_requests_model ON requests(model);

            CREATE TABLE IF NOT EXISTS system_metrics (
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

            CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_metrics(timestamp);

            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        logger.info(f"Database initialized at {Config.DB_PATH}")
    finally:
        conn.close()


def store_request_metric(data: dict):
    """Store a request metric record."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO requests
               (endpoint, model, status_code, error,
                prompt_tokens, completion_tokens, total_tokens,
                prompt_ms, predicted_ms,
                prompt_tokens_per_second, generation_tokens_per_second,
                total_latency_ms, time_to_first_token_ms,
                request_body_size, response_body_size)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("endpoint"),
                data.get("model"),
                data.get("status_code"),
                data.get("error"),
                data.get("prompt_tokens", 0),
                data.get("completion_tokens", 0),
                data.get("total_tokens", 0),
                data.get("prompt_ms"),
                data.get("predicted_ms"),
                data.get("prompt_tokens_per_second"),
                data.get("generation_tokens_per_second"),
                data.get("total_latency_ms"),
                data.get("time_to_first_token_ms"),
                data.get("request_body_size"),
                data.get("response_body_size"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def store_error_metric(data: dict):
    """Store an error metric record."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO requests
               (endpoint, model, status_code, error, total_latency_ms)
               VALUES (?, ?, ?, ?, ?)""",
            (
                data.get("endpoint"),
                data.get("model"),
                data.get("status_code"),
                data.get("error"),
                data.get("total_latency_ms"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def store_system_metric(data: dict):
    """Store a system metric record."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO system_metrics
               (gpu_utilization, gpu_memory_used_mb, gpu_memory_total_mb,
                gpu_temperature, gpu_power_watts,
                cpu_usage, memory_used_mb, memory_total_mb,
                swap_used_mb, swap_total_mb)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("gpu_utilization"),
                data.get("gpu_memory_used_mb"),
                data.get("gpu_memory_total_mb"),
                data.get("gpu_temperature"),
                data.get("gpu_power_watts"),
                data.get("cpu_usage"),
                data.get("memory_used_mb"),
                data.get("memory_total_mb"),
                data.get("swap_used_mb"),
                data.get("swap_total_mb"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_requests(start: str = None, end: str = None, model: str = None, limit: int = 100, offset: int = 0):
    """Query request metrics with optional filtering."""
    conn = _get_connection()
    try:
        query = "SELECT * FROM requests WHERE 1=1"
        params = []

        if start:
            query += " AND timestamp >= ?"
            params.append(start)
        if end:
            query += " AND timestamp <= ?"
            params.append(end)
        if model:
            query += " AND model = ?"
            params.append(model)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_system_metrics(start: str = None, end: str = None, limit: int = 500):
    """Query system metrics with optional date filtering."""
    conn = _get_connection()
    try:
        query = "SELECT * FROM system_metrics WHERE 1=1"
        params = []

        if start:
            query += " AND timestamp >= ?"
            params.append(start)
        if end:
            query += " AND timestamp <= ?"
            params.append(end)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_summary(start: str = None, end: str = None):
    """Get aggregate summary statistics."""
    conn = _get_connection()
    try:
        query = """
            SELECT
                COUNT(*) as total_requests,
                SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) as successful_requests,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_all_tokens,
                AVG(total_latency_ms) as avg_latency_ms,
                AVG(prompt_tokens_per_second) as avg_prompt_tps,
                AVG(generation_tokens_per_second) as avg_generation_tps,
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest
            FROM requests WHERE 1=1
        """
        params = []
        if start:
            query += " AND timestamp >= ?"
            params.append(start)
        if end:
            query += " AND timestamp <= ?"
            params.append(end)

        cursor = conn.execute(query, params)
        row = cursor.fetchone()
        if row:
            result = dict(row)
            total = result["total_requests"] or 0
            successful = result["successful_requests"] or 0
            result["successful_requests"] = successful
            result["total_prompt_tokens"] = result["total_prompt_tokens"] or 0
            result["total_completion_tokens"] = result["total_completion_tokens"] or 0
            result["total_all_tokens"] = result["total_all_tokens"] or 0
            result["success_rate"] = round((successful / total) * 100, 1) if total > 0 else 0
            return result
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_all_tokens": 0,
            "avg_latency_ms": None,
            "avg_prompt_tps": None,
            "avg_generation_tps": None,
            "success_rate": 0,
            "earliest": None,
            "latest": None,
        }
    finally:
        conn.close()


def get_models():
    """Get distinct model names from request history."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT DISTINCT model FROM requests WHERE model IS NOT NULL ORDER BY model"
        )
        return [row["model"] for row in cursor.fetchall()]
    finally:
        conn.close()


def cleanup_old_records(days: int = None):
    """Delete records older than retention period."""
    if days is None:
        days = Config.RETENTION_DAYS

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    conn = _get_connection()
    try:
        req_deleted = conn.execute(
            "DELETE FROM requests WHERE timestamp < ?", (cutoff,)
        ).rowcount
        sys_deleted = conn.execute(
            "DELETE FROM system_metrics WHERE timestamp < ?", (cutoff,)
        ).rowcount
        conn.commit()
        logger.info(f"Retention cleanup: removed {req_deleted} request records, {sys_deleted} system records (cutoff: {cutoff})")
        return req_deleted + sys_deleted
    finally:
        conn.close()



