FROM python:3.12-slim

# pynvml uses libnvidia-ml.so at runtime from the host GPU driver
# no dev packages needed inside the container
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY static/ static/

# Create data directory
RUN mkdir -p /data

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8008

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8008/health')" || exit 1

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8008"]
