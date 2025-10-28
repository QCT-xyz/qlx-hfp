# Dockerfile
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# system deps for cryptography and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libssl-dev curl \
    && rm -rf /var/lib/apt/lists/*

# app deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# app code
COPY src ./src
COPY scripts ./scripts
COPY schemas ./schemas

# runtime env
ENV PYTHONPATH=/app/src
ENV PORT=8080

# single healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

# json-form CMD via entrypoint
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
