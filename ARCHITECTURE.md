# ARCHITECTURE.md

This file provides guidance when working with code in this repository.

## Project Overview

MCP Xiaozhi is a WebSocket-to-stdio bridge for integrating Python-based MCP tools with remote systems. It manages communication between local MCP servers and WebSocket endpoints.

## Architecture

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

## Data Flow

```
┌─────────────┐      WebSocket      ┌─────────────┐      stdio      ┌─────────────┐
│  Web Hub    │ ◄─────────────────► │  mcp_pipe   │ ◄──────────────► │ MCP Server  │
│ (server.py) │                     │             │                  │ (FastMCP)   │
└─────────────┘                     └─────────────┘                  └─────────────┘
```

1. `mcp_pipe.py` reads `MCP_ENDPOINT` and `mcp_config.json`
2. Connects to WebSocket endpoint for each enabled server
3. Spawns MCP server subprocess (e.g., `calculator_server.py`)
4. Pipes WebSocket messages to subprocess stdin
5. Pipes subprocess stdout back to WebSocket
6. Logs subprocess stderr to terminal

## Setup

```bash
# Install package
pip install -e .

# Or use requirements.txt
pip install -r requirements.txt
```

## Running

```bash
# Terminal 1: Web Hub
cd web && python3 server.py

# Terminal 2: MCP Servers
export MCP_ENDPOINT=ws://localhost:8889/mcp
python3 mcp_pipe.py
```

## Configuration

### Environment Variables (`.env`)
```bash
MCP_ENDPOINT=ws://localhost:8889/mcp
```

### Server Config (`mcp_config.json`)
```json
{
  "mcpServers": {
    "calculator": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp_server/calculator_server.py"]
    },
    "search_and_news": {
      "type": "stdio", 
      "command": "python",
      "args": ["mcp_server/search_server.py"]
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
├── src/mcp_xiaozhi/          # Core bridge package
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
├── web/                      # Web interface (unchanged)
├── pyproject.toml            # Project config & dependencies
├── requirements.txt          # Legacy dependencies
├── mcp_config.json           # MCP server definitions
└── mcp_pipe.py               # Entry point wrapper
```