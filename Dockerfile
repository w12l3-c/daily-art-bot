# Use the official Python slim image (multi-arch, works on Raspberry Pi)
FROM python:3.12-slim

# Create app directory
WORKDIR /app

# Install system dependencies and clean up in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your bot code (excluding files via .dockerignore)
COPY . .

# Create directories for data persistence
RUN mkdir -p /app/badges

# Bot connects out, no ports needed
# Environment variables should be provided via --env-file or docker-compose

CMD ["python", "bot.py"]
