# syntax=docker/dockerfile:1

# ============================================================================
# Stage 1: Build the React frontend
# ============================================================================
FROM node:22-alpine AS frontend-build

WORKDIR /app

COPY FrontEnd/RankingPage/package.json FrontEnd/RankingPage/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY FrontEnd/RankingPage/ ./
RUN npm run build

# ============================================================================
# Stage 2: Backend runtime
# ============================================================================
FROM python:3.11-slim AS backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# OS deps for building any wheels needed at install time
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY BackEnd/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY BackEnd/ ./

# Non-root runtime user
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--timeout-keep-alive", "60"]

# ============================================================================
# Stage 3: Frontend web server (nginx) - built from the frontend-build stage
# ============================================================================
FROM nginxinc/nginx-unprivileged:1.27-alpine AS web

COPY FrontEnd/RankingPage/deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO /dev/null http://127.0.0.1:8080/ || exit 1
