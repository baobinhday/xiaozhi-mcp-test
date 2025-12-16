# Web-CMS Backend Architecture

This document describes the modular backend architecture for the MCP Endpoints CMS.

## Directory Structure

```
web-cms/
├── backend/                    # Python backend package
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration & settings
│   ├── dependencies.py         # FastAPI auth dependencies
│   ├── schemas/                # Pydantic request/response models
│   │   ├── auth.py             # LoginRequest
│   │   ├── endpoints.py        # EndpointCreate, EndpointUpdate
│   │   ├── mcp_servers.py      # MCPServerCreate, MCPServerUpdate
│   │   └── mcp_tools.py        # ToolToggle, ToolUpdate, etc.
│   ├── services/               # Business logic layer
│   │   ├── session.py          # Session & rate limiting
│   │   ├── mcp_config.py       # MCP config file operations
│   │   └── tool_discovery.py   # MCP server tool discovery
│   └── routes/                 # API route handlers
│       ├── auth.py             # /api/login, /api/logout
│       ├── endpoints.py        # /api/endpoints/*
│       ├── mcp_servers.py      # /api/mcp-servers/*
│       └── mcp_tools.py        # /api/mcp-tools/*
├── server.py                   # Entry point (wrapper)
├── index.html                  # SPA frontend
├── style.css                   # Styles
└── js/                         # Frontend JavaScript modules
```

## Layer Responsibilities

### Config (`config.py`)
- Environment variables loading
- Path definitions (CMS_DIR, MCP_CONFIG_PATH, TOOLS_CACHE_PATH)
- Auth settings (credentials, session duration)
- Rate limiting constants
- Logging configuration

### Schemas (`schemas/`)
Pydantic models for request/response validation:
- **auth.py**: `LoginRequest`
- **endpoints.py**: `EndpointCreate`, `EndpointUpdate`
- **mcp_servers.py**: `MCPServerCreate`, `MCPServerUpdate`
- **mcp_tools.py**: `ToolToggle`, `ToolUpdate`, `ToolReset`, `ToolRefresh`

### Services (`services/`)
Business logic, isolated from HTTP layer:
- **session.py**: Session CRUD, rate limiting, token management
- **mcp_config.py**: Load/save mcp_config.json, cache management
- **tool_discovery.py**: MCP server stdio protocol for tool discovery

### Dependencies (`dependencies.py`)
FastAPI dependency injection:
- `require_auth`: Validates session cookie, raises 401 if invalid

### Routes (`routes/`)
API endpoint handlers using APIRouter:
- **auth.py**: Login, logout, auth check
- **endpoints.py**: CRUD + SSE streaming + backup/restore
- **mcp_servers.py**: CRUD + backup/restore + tool discovery triggers
- **mcp_tools.py**: Toggle, update, reset, backup/restore, refresh

### Main (`main.py`)
FastAPI application assembly:
- Creates app with CORS middleware
- Includes all routers
- Mounts static files
- Defines `main()` entry point with uvicorn

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/login` | POST | Authenticate user |
| `/api/logout` | POST | Destroy session |
| `/api/auth/check` | GET | Check auth status |
| `/api/endpoints` | GET | List all endpoints |
| `/api/endpoints` | POST | Create endpoint |
| `/api/endpoints/{id}` | GET/PUT/DELETE | CRUD operations |
| `/api/endpoints/stream` | GET | SSE status stream |
| `/api/backup` | GET | Download endpoints backup |
| `/api/restore` | POST | Restore endpoints |
| `/api/mcp-servers` | GET | List MCP servers |
| `/api/mcp-servers` | POST | Create MCP server |
| `/api/mcp-servers/{name}` | PUT/DELETE | Update/delete server |
| `/api/mcp-config/backup` | GET | Download MCP config |
| `/api/mcp-config/restore` | POST | Restore MCP config |
| `/api/mcp-tools` | GET | Get tool settings |
| `/api/mcp-tools/cache` | GET | Get discovered tools |
| `/api/mcp-tools/toggle` | POST | Enable/disable tool |
| `/api/mcp-tools/update` | POST | Update tool metadata |
| `/api/mcp-tools/reset` | POST | Reset tool to defaults |
| `/api/mcp-tools/backup` | GET | Download tool config |
| `/api/mcp-tools/restore` | POST | Restore tool config |
| `/api/mcp-tools/refresh` | POST | Re-discover tools |

## Running the Server

```bash
# Standard entry point
python3 server.py

# Or directly via backend module
python3 -m backend.main

# Custom port
python3 server.py 9000
```

Default: http://localhost:8890

## Data Files

| File | Purpose |
|------|---------|
| `data/mcp_config.json` | MCP server configurations |
| `data/tools_cache.json` | Discovered tools cache |
| `data/mcp_database.db` | SQLite database (endpoints, tool settings) |
