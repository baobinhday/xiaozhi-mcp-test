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

Then open:
- **Web UI**: http://localhost:8888
- **CMS Admin**: http://localhost:8890

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
  -p 8890:8890 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
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

### Environment Variables

- `MCP_CONFIG`: Path to MCP config file (default: `/app/data/mcp_config.json`)
- `CONTEXT7_API_KEY`: API Key for Context7 (required if using Context7 tool)
- `PERPLEXITY_API_KEY`: API Key for Perplexity (required if using Perplexity tool)
- `CMS_USERNAME`: CMS admin username (default: `admin`)
- `CMS_PASSWORD`: CMS admin password (default: `changeme`)
- `CMS_SECRET_KEY`: CMS session secret key (default: `your-secret-key-here`)
- `WEB_USERNAME`: Web UI auth username (default: `admin`)
- `WEB_PASSWORD`: Web UI auth password (default: `admin123`)
- `WEB_SECRET_KEY`: Web UI session secret key (default: `your-web-secret-key-here`)

**Note:** Endpoints are configured via the CMS web interface at http://localhost:8890

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
- **8890**: CMS Admin Panel

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
  -p 8890:8890 \
  -v $(pwd):/app \
  mcp-web-tester
```

**Note**: When mounting volumes, the virtual environment in the container will be overridden. Make sure dependencies are installed in your mounted directory.
