# GPU and System Monitoring Research

## NVIDIA GPU Monitoring

### pynvml (Python NVML)
- Direct access to NVIDIA Management Library
- No need to shell out to `nvidia-smi`
- Provides: GPU utilization, memory usage, temperature, power draw, clock speeds
- Requires NVIDIA drivers on host, accessible via Docker `--gpus all`

### Key Metrics to Collect
- GPU utilization (%)
- GPU memory used / total (MB)
- GPU temperature (°C)
- GPU power draw (W)
- GPU clock speeds (MHz)

### Collection Frequency
- Every 5-10 seconds for GPU stats
- Store as time-series points in SQLite

## CPU/Memory Monitoring

### psutil
- Cross-platform system monitoring
- Provides: CPU usage (%), memory usage (used/total), swap
- Lightweight, no extra dependencies

### Key Metrics to Collect
- CPU usage per core and overall (%)
- Memory used / total (MB)
- Swap usage

### Collection Frequency
- Every 10-30 seconds (less critical than GPU)

## Docker GPU Access
```yaml
services:
  llm-monitor:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

Or via `docker run --gpus all`.

## Data Flow
1. Background task polls GPU/CPU every N seconds
2. Writes to `system_metrics` table in SQLite
3. Dashboard queries aggregate stats for display
4. Real-time WebSocket pushes latest values
