FROM python:3.14-slim

# Install curl for debugging
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Run the API as a dedicated unprivileged account.
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home \
    --shell /usr/sbin/nologin app

# Set working directory
WORKDIR /app

# Copy project metadata and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy Python scripts
COPY src/ ./src/

# Create log directory
RUN mkdir -p /var/log/agent \
    && chown app:app /var/log/agent

# Keep logs immediate and the application filesystem read-only at runtime.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

# Run the agentic RAG retrieval API
CMD ["sh", "-c", "python -m uvicorn src.main:app --host 0.0.0.0 --port ${AGENT_BACKEND_PORT:-8000}"]
