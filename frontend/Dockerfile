FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server.py .
COPY starters.py .
COPY static static

# Do not buffer Python output
ENV PYTHONUNBUFFERED=1

# Internal port (published only via the local profile / Caddy reverse proxy)
EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
