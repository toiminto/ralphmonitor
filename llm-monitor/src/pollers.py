"""GPU and CPU system pollers."""

import asyncio
import logging

import psutil

from src.config import Config
from src.storage import store_system_metric
from src.websocket import broadcaster

logger = logging.getLogger(__name__)

# GPU available flag
_gpu_available = None


async def gpu_poller():
    """Poll GPU metrics at configured interval."""
    global _gpu_available
    try:
        import pynvml
        pynvml.nvmlInit()
        _gpu_available = True
        logger.info("GPU poller started (pynvml initialized)")
    except Exception as e:
        _gpu_available = False
        logger.warning(f"GPU polling disabled: {e}")
        return

    try:
        while True:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)

                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW to W
                except Exception:
                    power = None

                metric = {
                    "gpu_utilization": float(utilization),
                    "gpu_memory_used_mb": round(mem_info.used / (1024 * 1024), 1),
                    "gpu_memory_total_mb": round(mem_info.total / (1024 * 1024), 1),
                    "gpu_temperature": float(temperature),
                    "gpu_power_watts": round(power, 1) if power else None,
                    "cpu_usage": None,
                    "memory_used_mb": None,
                    "memory_total_mb": None,
                    "swap_used_mb": None,
                    "swap_total_mb": None,
                }

                store_system_metric(metric)
                asyncio.create_task(broadcaster.broadcast_system_metric(metric))
            except Exception as e:
                logger.error(f"GPU poll error: {e}")

            await asyncio.sleep(Config.GPU_POLL_INTERVAL)
    except asyncio.CancelledError:
        logger.info("GPU poller stopped")
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass


async def system_poller():
    """Poll CPU/memory metrics at configured interval."""
    logger.info("System poller started")
    try:
        while True:
            try:
                cpu_usage = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                swap = psutil.swap_memory()

                metric = {
                    "gpu_utilization": None,
                    "gpu_memory_used_mb": None,
                    "gpu_memory_total_mb": None,
                    "gpu_temperature": None,
                    "gpu_power_watts": None,
                    "cpu_usage": cpu_usage,
                    "memory_used_mb": round(mem.used / (1024 * 1024), 1),
                    "memory_total_mb": round(mem.total / (1024 * 1024), 1),
                    "swap_used_mb": round(swap.used / (1024 * 1024), 1),
                    "swap_total_mb": round(swap.total / (1024 * 1024), 1),
                }

                store_system_metric(metric)
                asyncio.create_task(broadcaster.broadcast_system_metric(metric))
            except Exception as e:
                logger.error(f"System poll error: {e}")

            await asyncio.sleep(Config.CPU_POLL_INTERVAL)
    except asyncio.CancelledError:
        logger.info("System poller stopped")


async def retention_cleaner():
    """Clean up old records at configured interval."""
    from src.storage import cleanup_old_records
    logger.info(f"Retention cleaner started (interval: {Config.CLEANUP_INTERVAL}s)")
    try:
        while True:
            await asyncio.sleep(Config.CLEANUP_INTERVAL)
            try:
                deleted = cleanup_old_records()
                if deleted:
                    logger.info(f"Cleaned up {deleted} old records")
            except Exception as e:
                logger.error(f"Retention cleanup error: {e}")
    except asyncio.CancelledError:
        logger.info("Retention cleaner stopped")


# Background task handles
_gpu_task = None
_system_task = None
_cleanup_task = None


async def start_pollers():
    """Start all background poller tasks."""
    global _gpu_task, _system_task, _cleanup_task
    _gpu_task = asyncio.create_task(gpu_poller())
    _system_task = asyncio.create_task(system_poller())
    _cleanup_task = asyncio.create_task(retention_cleaner())
    logger.info("All pollers started")


async def stop_pollers():
    """Stop all background poller tasks."""
    global _gpu_task, _system_task, _cleanup_task
    for task in [_gpu_task, _system_task, _cleanup_task]:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    logger.info("All pollers stopped")
