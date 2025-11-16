FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git cron \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and configuration files
COPY src/ ./src/
COPY index_config.yml .

# Do not buffer Python output 
ENV PYTHONUNBUFFERED=1

# Schedule cron job for index pipeline with one immediate pipeline execution
ENTRYPOINT ["python", "-m", "src.entrypoint", "--run-immediately"]
