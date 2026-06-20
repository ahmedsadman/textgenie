FROM python:3.12.13-slim AS dev

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM python:3.12.13-slim AS production

RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -d /app -s /bin/false appuser

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

COPY --from=dev --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=dev --chown=appuser:appgroup /app/app /app/app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
