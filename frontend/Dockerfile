FROM python:3.14-slim

# Run the web server as a dedicated unprivileged account.
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home \
    --shell /usr/sbin/nologin app

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application
COPY server.py .
COPY starters.py .
COPY static static

# Keep logs immediate and the application filesystem read-only at runtime.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

# Internal port (published only via the local profile / Caddy reverse proxy)
EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
