# Use a lightweight official Python runtime
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy unpinned requirements
COPY requirements.txt .

# Compile requirements specifically for the Linux target
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip compile requirements.txt -o requirements.lock && \
    uv pip sync --system requirements.lock

# Copy application code
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]