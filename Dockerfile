FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV VECNA_TRANSPORT=http

# Render injects $PORT at runtime; server.py binds 0.0.0.0:$PORT.
EXPOSE 8000
CMD ["vecna"]
