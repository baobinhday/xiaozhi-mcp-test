# Use Python 3.12 slim base image
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install dependencies in a separate stage for better caching
FROM base as dependencies

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM base as final

# Copy installed packages from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Expose ports
# 8888 for web UI
# 8889 for WebSocket hub
EXPOSE 8888 8889

# Runtime environment variables (can be overridden with -e or docker-compose)
ENV MCP_ENDPOINT=ws://localhost:8889/mcp \
    MCP_CONFIG=/app/mcp_config.json

# Create a startup script to run both services
RUN echo '#!/bin/bash\n\
    set -e\n\
    \n\
    # Start the web server in the background\n\
    echo "Starting Web Server..."\n\
    cd /app/web && python3 server.py &\n\
    WEB_PID=$!\n\
    \n\
    # Wait a bit for the web server to start\n\
    sleep 2\n\
    \n\
    # Start the MCP pipe\n\
    echo "Starting MCP Pipe..."\n\
    cd /app && python3 mcp_pipe.py &\n\
    MCP_PID=$!\n\
    \n\
    # Wait for both processes\n\
    wait $WEB_PID $MCP_PID\n\
    ' > /app/start.sh && chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import socket; s=socket.socket(); s.connect(('localhost', 8888)); s.close()" || exit 1

# Default command
CMD ["/app/start.sh"]
