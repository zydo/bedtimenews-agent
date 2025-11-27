FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Chainlit app files
COPY app.py .
COPY starters.py .
COPY chainlit.md .
COPY .chainlit .chainlit
COPY public public

# Do not buffer Python output
ENV PYTHONUNBUFFERED=1

# Expose Chainlit default port
EXPOSE 8000

# Run Chainlit app
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
