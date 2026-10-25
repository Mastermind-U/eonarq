FROM ghcr.io/astral-sh/uv:0.11.1 AS uv
FROM python:3.14-slim AS builder
COPY --from=uv /uv /uvx /bin/
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-default-groups --no-install-project
COPY src ./src
RUN uv sync --locked --no-default-groups --no-editable

FROM python:3.14-slim
LABEL org.opencontainers.image.source="https://github.com/Mastermind-U/eonarq" \
      org.opencontainers.image.description="Local epic and prompt tracker with MCP" \
      org.opencontainers.image.licenses="GPL-3.0-only"
RUN groupadd --system eonarq && useradd --system --gid eonarq --home-dir /app eonarq \
    && mkdir -p /data && chown eonarq:eonarq /data
WORKDIR /app
COPY --from=builder --chown=eonarq:eonarq /app/.venv /app/.venv
COPY LICENSE ./LICENSE
ENV PATH="/app/.venv/bin:$PATH" \
    EONARQ_DATABASE_URL="sqlite:////data/eonarq.sqlite3" \
    EONARQ_HOST="0.0.0.0" EONARQ_PORT="8765" \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER eonarq
EXPOSE 8765
VOLUME ["/data"]
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=2)"]
ENTRYPOINT ["eonarq"]
