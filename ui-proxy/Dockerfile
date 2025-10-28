FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY ui-proxy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ui-proxy ./ui-proxy
ENV PORT=8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD curl -fsS "http://127.0.0.1:${PORT}/" || exit 1
CMD ["uvicorn", "ui-proxy.app:app", "--host", "0.0.0.0", "--port", "8080"]
