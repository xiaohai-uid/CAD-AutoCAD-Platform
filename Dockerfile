# Windows-based Docker image for CAD Direct Control Platform
# Note: COM automation requires Windows containers
FROM python:3.11-windowsservercore-1809 AS base

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports for all services
EXPOSE 8000 8001 8002 8003 8004 8005 8006 8007 8008

# Default: run a specific service via CMD override
CMD ["python", "-m", "services.gateway.main"]
