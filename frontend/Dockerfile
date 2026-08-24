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

# Plain HTTP port, published to the host by docker-compose (FRONTEND_PORT).
# TLS termination and public exposure are handled outside this repo.
EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
