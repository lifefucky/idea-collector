# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend
WORKDIR /web
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci
COPY webapp/ ./
RUN npm run build

FROM python:3.12-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_NO_DEV=1
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --no-editable
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.12-slim-trixie
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot \
    && mkdir -p /data \
    && chown nonroot:nonroot /data
COPY --from=builder --chown=nonroot:nonroot /app/.venv /app/.venv
COPY --from=frontend --chown=nonroot:nonroot /web/dist /app/webapp/dist
ENV PORT=8080 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
WORKDIR /app
USER nonroot
EXPOSE 8080
STOPSIGNAL SIGINT
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/' % os.environ.get('PORT', '8080'), timeout=4)"
CMD ["idea-collector"]
