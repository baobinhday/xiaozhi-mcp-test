# CLAUDE.md

This file provides guidance to anyone when working with code in this repository.

## Project Overview

MCP Xiaozhi is a WebSocket-to-stdio bridge for integrating Python-based MCP (Model Context Protocol) tools with remote systems. It manages communication between local MCP servers and WebSocket endpoints through a central hub.

## Architecture

### Core Components

The system consists of three main components:

1. **Web Hub (`web/server.py`)**: WebSocket server that acts as a central hub, managing connections between browser UI and MCP tools
2. **Web Client (`http://localhost:8888`)**: Browser interface that connects to the hub to send tool requests
3. **MCP Pipe (`mcp_pipe.py`)**: Connects to the hub to execute requests from configured MCP servers

### Data Flow

```
┌─────────────┐      WebSocket      ┌─────────────┐      stdio      ┌─────────────┐
│  Web Hub    │ ◄─────────────────► │  mcp_pipe   │ ◄──────────────► │ MCP Server  │
│ (server.py) │                     │             │                  │ (FastMCP)   │
└─────────────┘                     └─────────────┘                  └─────────────┘
```

1. `mcp_pipe.py` reads endpoints from SQLite database and `mcp_config.json`
2. Connects to WebSocket endpoints for each enabled server
3. Spawns MCP server subprocess (e.g., `calculator_server.py`)
4. Pipes WebSocket messages to subprocess stdin
5. Pipes subprocess stdout back to WebSocket
6. Logs subprocess stderr to terminal

### Core Package (`src/mcp_xiaozhi/`)

| Module | Purpose |
|--------|---------|
| `main.py` | Entry point, server orchestration |
| `config.py` | Configuration loading from `.env` and `mcp_config.json` |
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

### Server Config (`mcp_config.json`)
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

3. Add to `mcp_config.json`:
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
├── web/                      # Web interface and hub
│   ├── server.py             # WebSocket hub
│   ├── index.html            # Web UI
│   └── app.js                # Client-side JavaScript
├── pyproject.toml            # Project config & dependencies
├── requirements.txt          # Legacy dependencies
├── mcp_config.json           # MCP server definitions
├── mcp_pipe.py               # Entry point wrapper
└── ARCHITECTURE.md           # Architecture documentation
```