# ════════════════════════════════════════════════════════════════════
#  DataFlow Studio — Multi-stage Dockerfile
#  Stage 1: Build React frontend
#  Stage 2: Production Python + Flask server
# ════════════════════════════════════════════════════════════════════

# ── Stage 1: Frontend build ───────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend ───────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

# Minimal system deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY api/         ./api/
COPY data/        ./data/
COPY .env.example ./.env.example

# Copy built frontend
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Non-root user for security
RUN useradd -m -r appuser && chown -R appuser:appuser /app
USER appuser

# Runtime config
ENV ENVIRONMENT=production
ENV DEBUG=false
ENV PORT=5000
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')"

CMD ["python", "api/index.py"]
