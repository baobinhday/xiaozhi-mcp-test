# ARCHITECTURE.md

This file provides guidance to anyone when working with code in this repository.

## Project Overview

MCP Xiaozhi is a WebSocket-to-stdio bridge for integrating Python-based MCP (Model Context Protocol) tools with remote systems. It manages communication between local MCP servers and WebSocket endpoints through a central hub.

## Architecture

### Three Main Components

The system consists of three independent components with **clear separation of concerns**:

| Component | Port | Purpose | Connects to Hub? |
|-----------|------|---------|------------------|
| **Web Hub** (`web/`) | 8888 (HTTP), 8889 (WS) | Runtime - serves browser UI & manages tool execution | N/A (IS the hub) |
| **Web CMS** (`web-cms/`) | 8890 | Admin - configuration management only | ❌ **NO** |
| **MCP Pipe** (`mcp_pipe.py`) | N/A (client) | Bridge - connects MCP servers to hub | ✅ Yes |

### Component Details

#### 1. Web Hub (`web/server.py`) - Runtime Layer
- **Role**: Central WebSocket hub for tool execution
- **Features**:
  - Serves browser-based MCP Tools Tester UI
  - Manages WebSocket connections between browser clients and MCP tools
  - Aggregates tools from multiple MCP servers
  - Forwards tool requests and returns results
- **Users**: End users testing/using MCP tools

#### 2. Web CMS (`web-cms/server.py`) - Configuration Layer
- **Role**: Admin panel for managing configuration files
- **Important**: The CMS **NEVER** connects to the Hub - it only manages files!
- **Manages**:
  - `data/app.db` - WebSocket endpoint URLs + tool settings (enable/disable, custom names)
  - `data/mcp_config.json` - MCP server definitions
  - `data/tools_cache.json` - Cached tool list from bridge (read-only)
- **Features**:
  - CRUD for endpoints and MCP servers
  - Enable/disable individual tools
  - Custom tool names/descriptions
  - Backup/restore for all configs
- **Users**: Administrators configuring the system

#### 3. MCP Pipe (`mcp_pipe.py` → `src/mcp_xiaozhi/`) - Bridge Layer
- **Role**: WebSocket-to-stdio bridge connecting MCP servers to the hub
- **Features**:
  - Reads config files that CMS manages
  - Spawns MCP server subprocesses
  - Pipes messages between WebSocket and subprocess stdio
  - Hot-reloads when config changes
  - Filters tools based on tool settings in `app.db`
  - Writes `tools_cache.json` for CMS to read
- **Users**: The system (runs as a background process)

### Data Flow Diagram

```
                        ┌─────────────────────────────────────────────────────────┐
                        │                    CONFIG FILES                         │
                        │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
                        │  │  app.db (endpoints + tool settings)  │ │mcp_config.json│ │
                        │  └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘ │
                        │         │                │                   │          │
                        └─────────┼────────────────┼───────────────────┼──────────┘
                                  │                │                   │
                    ┌─────────────┴────────────────┴───────────────────┴───────────┐
                    │                                                              │
         Writes ◄───┤                      web-cms/                                │
         Reads  ───►│                    (Admin Panel)                             │
                    │                     Port 8890                                │
                    └──────────────────────────────────────────────────────────────┘
                                                    ▲
                                                    │ (NO connection)
                                                    ✗
                                                    
                    ┌──────────────────────────────────────────────────────────────┐
                    │                                                              │
         Reads  ───►│                      mcp_pipe.py                             │
                    │                    (Bridge Layer)                            │
                    │                                                              │
                    └─────────────────────────────┬────────────────────────────────┘
                                                  │
                                                  │ WebSocket
                                                  ▼
┌───────────────┐                    ┌─────────────────────────┐                    ┌───────────────┐
│               │     WebSocket      │                         │       stdio        │               │
│   Browser     │◄──────────────────►│        web/             │◄──────────────────►│  MCP Servers  │
│   (User UI)   │                    │   (WebSocket Hub)       │   (via mcp_pipe)   │  (FastMCP)    │
│               │                    │   Port 8888/8889        │                    │               │
└───────────────┘                    └─────────────────────────┘                    └───────────────┘
```

### Data Flow Steps

1. **Admin configures** via CMS → writes to config files
2. **mcp_pipe.py reads** config files (endpoints, MCP servers, tool filters)
3. **mcp_pipe.py connects** to Hub via WebSocket
4. **mcp_pipe.py spawns** MCP server subprocesses
5. **Browser connects** to Hub via WebSocket
6. **Hub forwards** tool requests from browser → mcp_pipe → MCP server
7. **Hub returns** results from MCP server → mcp_pipe → browser

### Core Package (`src/mcp_xiaozhi/`)

| Module | Purpose |
|--------|---------|
| `main.py` | Entry point, server orchestration |
| `config.py` | Configuration loading from `.env` and `data/mcp_config.json` |
| `connection.py` | WebSocket connection with exponential backoff retry |
| `pipe.py` | stdin/stdout/stderr piping between WebSocket and subprocess |
| `server_builder.py` | Build server commands from config |
| `utils.py` | Shared utilities (logging, Windows encoding fix) |

### Tools Package (`tools/`)

| Tool | Function | Description |
|------|----------|-------------|
| `math_tools.py` | `calculator()` | Safe mathematical expression evaluation |
| `search_tools.py` | `web_search()` | DuckDuckGo web search |
| `news_tools.py` | `get_latest_news()` | VNExpress RSS news fetching |

### MCP Servers (`mcp_server/`)

| Server | Tools Exposed |
|--------|---------------|
| `calculator_server.py` | `calculator` |
| `search_server.py` | `get_latest_news` |

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package with dependencies
pip install -e .

# Or install with dev tools (ruff, mypy, pytest)
pip install -e ".[dev]"

# Or use requirements.txt
pip install -r requirements.txt
```

### Running the System

```bash
# Terminal 1: Web Hub
cd web
python3 server.py

# Terminal 2: MCP Tools
python3 mcp_pipe.py
```

### Alternative Run Options
```bash
# Run a specific server script
python3 mcp_pipe.py mcp_server/calculator_server.py

# Using the installed command
mcp-pipe

# Run with specific server
mcp-pipe mcp_server/calculator_server.py
```

### Development Tools

```bash
# Linting with ruff
ruff check src/ tools/ mcp_server/

# Type checking with mypy
mypy src/ tools/ mcp_server/

# Run tests (if any exist)
pytest

# Format code with ruff
ruff format src/ tools/ mcp_server/
```

### Endpoint Configuration

Endpoints are configured via the CMS at http://localhost:8890:

```bash
# Start the CMS server
cd web-cms && python3 server.py
```

Default credentials: `admin` / `changeme` (configure via `CMS_USERNAME`, `CMS_PASSWORD` in `.env`)

### Server Config (`data/mcp_config.json`)
```json
{
  "mcpServers": {
    "calculator": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp_server/calculator_server.py"],
      "disabled": false
    },
    "search_and_news": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp_server/search_server.py"]
    },
    "perplexity": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "perplexity-mcp"
      ],
      "env": {
        "PERPLEXITY_API_KEY": "${PERPLEXITY_API_KEY}"
      }
    }
  }
}
```

## Adding New Tools

1. Create tool function in `tools/`:
   ```python
   # tools/my_tools.py
   def my_tool(param: str) -> dict:
       """Tool description."""
       return {"success": True, "result": "..."}
   ```

2. Create MCP server in `mcp_server/`:
   ```python
   # mcp_server/my_server.py
   import os, sys
   sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

   from mcp.server.fastmcp import FastMCP
   from tools.my_tools import my_tool

   mcp = FastMCP("MyServer")
   mcp.tool()(my_tool)

   if __name__ == "__main__":
       mcp.run(transport="stdio")
   ```

3. Add to `data/mcp_config.json`:
   ```json
   "my_server": {
     "type": "stdio",
     "command": "python",
     "args": ["mcp_server/my_server.py"]
   }
   ```

## Project Structure

```
├── src/mcp_xiaozhi/          # Core WebSocket-stdio bridge package
│   ├── __init__.py
│   ├── main.py               # Entry point
│   ├── config.py             # Configuration
│   ├── connection.py         # WebSocket handling
│   ├── pipe.py               # I/O piping
│   ├── server_builder.py     # Command building
│   └── utils.py              # Utilities
├── tools/                    # Tool implementations
│   ├── math_tools.py
│   ├── search_tools.py
│   └── news_tools.py
├── mcp_server/               # MCP server scripts
│   ├── calculator_server.py
│   └── search_server.py
├── web/                      # Runtime: WebSocket hub + browser UI
│   ├── server.py             # WebSocket hub server
│   ├── index.html            # MCP Tools Tester UI
│   └── js/                   # Client-side JavaScript modules
├── web-cms/                  # Admin: Configuration management only
│   ├── server.py             # REST API server (NO WebSocket connection to hub)
│   ├── index.html            # Admin dashboard UI
│   └── style.css             # Admin styles
├── data/                     # Data files (gitignored)
│   ├── app.db                # SQLite database for endpoints & tool settings
│   ├── mcp_config.json       # MCP server definitions
│   └── tools_cache.json      # Cached tools list from bridge
├── pyproject.toml            # Project config & dependencies
├── requirements.txt          # Legacy dependencies
├── mcp_config.example.json   # MCP server definitions template
├── mcp_pipe.py               # Entry point wrapper
└── ARCHITECTURE.md           # Architecture documentation
```