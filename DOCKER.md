# Docker Deployment Guide

This guide explains how to build and run the MCP Web Tester using Docker.

## Quick Start with Docker Compose

The easiest way to run the application:

```bash
# Build and start the container
docker compose up -d

# View logs
docker compose logs -f

# Stop the container
docker compose down
```

Then open http://localhost:8888 in your browser.

## Manual Docker Commands

### Build the Docker Image

```bash
docker build -t mcp-web-tester .
```

### Run the Container

```bash
docker run -d \
  --name mcp-tester \
  -p 8888:8888 \
  -p 8889:8889 \
  -e MCP_ENDPOINT=ws://localhost:8889/mcp \
  -e MCP_SCRIPT=agent_tools.py \
  mcp-web-tester
```

### View Container Logs

```bash
docker logs -f mcp-tester
```

### Stop and Remove Container

```bash
docker stop mcp-tester
docker rm mcp-tester
```

## Configuration

### Environment Variables

- `MCP_ENDPOINT`: WebSocket endpoint (default: `ws://localhost:8889/mcp`)
- `MCP_SCRIPT`: MCP script to run (default: `agent_tools.py`)

### Using a Different MCP Script

To run with a different script (e.g., `test/calculator.py`):

```bash
docker run -d \
  -p 8888:8888 \
  -p 8889:8889 \
  -e MCP_SCRIPT=test/calculator.py \
  mcp-web-tester
```

Or with docker compose, modify the `docker compose.yml`:

```yaml
environment:
  - MCP_SCRIPT=test/calculator.py
```

## Ports

- **8888**: Web UI
- **8889**: WebSocket Hub

## Health Check

The container includes a health check that verifies the web server is running. You can check the status:

```bash
docker ps  # Shows health status in the STATUS column
docker inspect --format='{{.State.Health.Status}}' mcp-tester
```

## Troubleshooting

### Check if container is running
```bash
docker ps
```

### View container logs
```bash
docker logs mcp-tester
```

### Access container shell
```bash
docker exec -it mcp-tester bash
```

### Rebuild without cache
```bash
docker compose build --no-cache
```

## Development

For development, you might want to mount your local code:

```bash
docker run -d \
  -p 8888:8888 \
  -p 8889:8889 \
  -v $(pwd):/app \
  -e MCP_SCRIPT=agent_tools.py \
  mcp-web-tester
```

**Note**: When mounting volumes, the virtual environment in the container will be overridden. Make sure dependencies are installed in your mounted directory.
