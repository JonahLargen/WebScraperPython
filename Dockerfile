FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    OUTPUT_DIR=/app/output

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev

COPY *.py ./

RUN useradd --create-home --uid 1000 crawler \
    && mkdir -p /app/output /tmp/matplotlib \
    && chown -R crawler:crawler /app /tmp/matplotlib

USER crawler

VOLUME ["/app/output"]

CMD ["uv", "run", "--no-sync", "scheduler.py"]
