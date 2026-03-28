FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Copy application code
COPY . .

# Railway sets PORT dynamically
ENV PORT=8000

EXPOSE ${PORT}

CMD uv run uvicorn main:app --host 0.0.0.0 --port ${PORT}
