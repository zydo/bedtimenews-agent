FROM python:3.12-slim

# Install curl for debugging
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python scripts
COPY src/ ./src/

# Create log directory
RUN mkdir -p /var/log/agent

# Do not buffer Python output
ENV PYTHONUNBUFFERED=1

# Run the agentic RAG retrieval API
CMD ["sh", "-c", "python -m uvicorn src.main:app --host 0.0.0.0 --port ${AGENT_BACKEND_PORT}"]
