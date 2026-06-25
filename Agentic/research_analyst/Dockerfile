# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — builder: install Python deps into an isolated --user prefix.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# System build deps occasionally needed by scientific wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 — runtime: copy the installed packages and the app source.
# ---------------------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Persistent/working directories (also mounted as volumes by docker-compose).
RUN mkdir -p /app/chroma_db /app/mlruns /app/uploads /app/eval_reports /app/sample_pdfs

EXPOSE 8000

CMD ["uvicorn", "serve.api:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]

