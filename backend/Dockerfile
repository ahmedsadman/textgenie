FROM python:3.12.13-slim AS dev

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

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

ENV PATH="/opt/venv/bin:$PATH" PYTHONPATH=/app

COPY --from=dev --chown=appuser:appgroup /opt/venv /opt/venv
COPY --from=dev --chown=appuser:appgroup /app/app /app/app
COPY --from=dev --chown=appuser:appgroup /app/alembic /app/alembic
COPY --from=dev --chown=appuser:appgroup /app/alembic.ini /app/alembic.ini
COPY --from=dev --chown=appuser:appgroup /app/scripts /app/scripts

USER appuser

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
