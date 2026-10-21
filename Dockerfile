# Automatic File Organizer & Backup System (Team 19)
# Stage 3: Docker Containerization with Flask Web Application & CLI

# Use official lightweight Python base image
FROM python:3.12-slim

# Prevent generation of .pyc files and enable unbuffered console output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000

# Set container working directory
WORKDIR /app

# Copy dependency manifests
COPY requirements.txt .

# Install dependencies (no cache to keep image size minimal)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application configuration, templates, static assets, and source code
COPY config/ ./config/
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/

# Copy entrypoint script and normalize line endings
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

# Create runtime directories for data mounting (input, backup, logs, web staging)
RUN mkdir -p /app/data/input /app/data/web_input /app/data/web_backup /app/backup /app/logs

# Expose Flask web service port
EXPOSE 5000

# Dispatcher entrypoint: defaults to Web App, forwards flags to CLI
ENTRYPOINT ["docker-entrypoint.sh"]
