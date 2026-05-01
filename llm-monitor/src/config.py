"""Environment configuration with defaults."""

import os


class Config:
    LLM_BACKEND_URL: str = os.getenv("LLM_BACKEND_URL", "http://localhost:8080")
    MONITOR_PORT: int = int(os.getenv("MONITOR_PORT", "8008"))
    DB_PATH: str = os.getenv("DB_PATH", "/data/metrics.db")
    RETENTION_DAYS: int = int(os.getenv("RETENTION_DAYS", "30"))
    GPU_POLL_INTERVAL: int = int(os.getenv("GPU_POLL_INTERVAL", "5"))
    CPU_POLL_INTERVAL: int = int(os.getenv("CPU_POLL_INTERVAL", "10"))
    CLEANUP_INTERVAL: int = int(os.getenv("CLEANUP_INTERVAL", "3600"))

    @classmethod
    def validate(cls):
        """Validate configuration values."""
        if not cls.LLM_BACKEND_URL:
            raise ValueError("LLM_BACKEND_URL must be set")
        if cls.MONITOR_PORT < 1 or cls.MONITOR_PORT > 65535:
            raise ValueError("MONITOR_PORT must be between 1 and 65535")
        if cls.RETENTION_DAYS < 1:
            raise ValueError("RETENTION_DAYS must be at least 1")
        if cls.GPU_POLL_INTERVAL < 1:
            raise ValueError("GPU_POLL_INTERVAL must be at least 1")
        if cls.CPU_POLL_INTERVAL < 1:
            raise ValueError("CPU_POLL_INTERVAL must be at least 1")
