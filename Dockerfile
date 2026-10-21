# syntax=docker/dockerfile:1
# One image for api, worker and migrate (ADR-0011): the frontend's build stage feeds
# the Python stage, and compose picks the command.

FROM node:24-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# The VPS is small and shared: cap Node's heap rather than let a build crowd it.
ENV NODE_OPTIONS=--max-old-space-size=512
RUN npm run build

FROM python:3.12-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1
WORKDIR /app
# Dependencies first, so a code change doesn't reinstall them.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --locked --no-dev --no-editable
COPY --from=web /web/dist /app/static
RUN useradd --system --uid 10001 --no-create-home swap
USER swap
ENV PATH=/app/.venv/bin:$PATH \
    STATIC_DIR=/app/static
EXPOSE 8000
CMD ["uvicorn", "swap.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
