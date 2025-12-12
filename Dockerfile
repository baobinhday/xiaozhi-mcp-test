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
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (includes uvx)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Install dependencies in a separate stage for better caching
FROM base as dependencies

WORKDIR /app

# Copy only package definition files first for better caching
COPY pyproject.toml .
COPY src/ src/

# Install package and dependencies
RUN pip install --no-cache-dir -e .

# Final stage
FROM base as final

# Copy installed packages from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create data directory and copy example configs (can be mounted over at runtime)
RUN mkdir -p /app/data && \
    cp /app/mcp_config.example.json /app/data/mcp_config.json

# Expose ports
# 8888 for web UI
# 8889 for WebSocket hub
# 8890 for CMS admin
EXPOSE 8888 8889 8890

# Runtime environment variables (can be overridden with -e or docker-compose)
ENV MCP_CONFIG=/app/data/mcp_config.json \
    PERPLEXITY_API_KEY="" \
    CMS_USERNAME=admin \
    CMS_PASSWORD=changeme \
    CMS_SECRET_KEY=your-secret-key-here \
    WEB_USERNAME=admin \
    WEB_PASSWORD=admin123 \
    WEB_SECRET_KEY=your-web-secret-key-here

# Create a startup script to run all services
RUN echo '#!/bin/bash\n\
    set -e\n\
    \n\
    # Ensure data directory exists and has config file\n\
    mkdir -p /app/data\n\
    if [ ! -f /app/data/mcp_config.json ]; then\n\
    echo "Creating mcp_config.json from example..."\n\
    cp /app/mcp_config.example.json /app/data/mcp_config.json\n\
    fi\n\
    # Start the web server in the background\n\
    echo "Starting Web Server on port 8888..."\n\
    cd /app/web && python3 server.py &\n\
    WEB_PID=$!\n\
    \n\
    # Start the CMS server in the background\n\
    echo "Starting CMS Server on port 8890..."\n\
    cd /app/web-cms && python3 server.py &\n\
    CMS_PID=$!\n\
    \n\
    # Wait a bit for the servers to start\n\
    sleep 2\n\
    \n\
    # Start the MCP pipe\n\
    echo "Starting MCP Pipe..."\n\
    cd /app && python3 mcp_pipe.py &\n\
    MCP_PID=$!\n\
    \n\
    # Wait for all processes\n\
    wait $WEB_PID $CMS_PID $MCP_PID\n\
    ' > /app/start.sh && chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import socket; s=socket.socket(); s.connect(('localhost', 8888)); s.close()" || exit 1

# Default command
CMD ["/app/start.sh"]
