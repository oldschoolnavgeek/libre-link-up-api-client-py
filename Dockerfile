# Dockerfile for LibreLinkUp Database Service
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY libre_link_up_client/ ./libre_link_up_client/
COPY service.py .
COPY setup.py .
COPY README.md .

# Install the package in development mode
RUN pip install -e .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run the service (API mode by default)
# For sync mode, override with: CMD ["python", "service.py", "sync"]
CMD ["python", "service.py"]

