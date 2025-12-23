# ARCHITECTURE.md

This file provides guidance to anyone when working with code in this repository.

## Project Overview

MCP Xiaozhi is a **distributed WebSocket-to-stdio bridge** for integrating Python-based MCP (Model Context Protocol) tools with multiple remote Web Hubs. The system supports **multiple Web Hub instances** running on different servers, with a centralized CMS managing all endpoint URLs and an MCP Pipe that connects to all configured hubs simultaneously.

## Architecture

### Three Main Components (Distributed Design)

The system consists of three independent components with **clear separation of concerns**:

| Component | Deployment | Purpose | Connects to Hub? |
|-----------|------------|---------|------------------|
| **Web Hub** (`web/`) | **Multiple servers** (each on port 8888/8889) | Runtime - serves browser UI & manages tool execution | N/A (IS the hub) |
| **Web CMS** (`web-cms/`) | Single instance (port 8890) | Admin - manages **all Web Hub endpoint URLs** | ❌ **NO** |
| **MCP Pipe** (`mcp_pipe.py`) | Single instance | Bridge - connects to **ALL Web Hub endpoints** | ✅ Yes (multiple) |

### Component Details

#### 1. Web Hub (`web/server.py`) - Runtime Layer (Multiple Instances)
- **Role**: WebSocket hub instance that provides tool testing interface
- **Deployment**: **Multiple independent instances** can run on different servers
- **Features**:
  - **Creates WebSocket endpoint URL** (e.g., ws://server1.example.com:8889, ws://server2.example.com:8889)
  - Serves browser-based **Web UI to test all tools** retrieved from MCP Pipe (after WebSocket connection)
  - Manages WebSocket connections between browser clients and MCP tools
  - Aggregates tools from multiple MCP servers via MCP Pipe
  - Forwards tool requests and returns results
- **Users**: End users testing/using MCP tools via the browser UI
- **Note**: Each Web Hub instance is independent; users connect to their nearest/assigned hub

#### 2. Web CMS (`web-cms/server.py`) - Configuration Layer (Single Instance)
- **Role**: Centralized admin panel for managing **all Web Hub endpoint URLs** and configurations
- **Deployment**: **Single instance** managing the entire distributed system
- **Important**: The CMS **NEVER** connects to the Hubs - it only manages configuration files!
- **Manages**:
  - `data/app.db` - **Multiple WebSocket endpoint URLs** from different Web Hub servers + tool settings (enable/disable, custom names)
  - `data/mcp_config.json` - MCP server definitions
  - `data/tools_cache.json` - Cached tool list from bridge (read-only)
- **Features**:
  - **Add/Edit/Delete WebSocket endpoint URLs** for multiple Web Hubs (e.g., ws://server1:8889, ws://server2:8889)
  - CRUD for MCP server configurations
  - Enable/disable individual tools (applies to ALL hubs)
  - Custom tool names/descriptions (applies to ALL hubs)
  - Backup/restore for all configs
- **Users**: System administrators managing the distributed infrastructure

#### 3. MCP Pipe (`mcp_pipe.py` → `src/mcp_xiaozhi/`) - Bridge Layer (Single Instance)
- **Role**: WebSocket-to-stdio bridge that connects MCP servers to **ALL Web Hub endpoints simultaneously**
- **Deployment**: **Single instance** broadcasting to all configured Web Hubs
- **Features**:
  - Reads config files that CMS manages (endpoints, MCP servers, tool settings)
  - **Connects to MULTIPLE Web Hub endpoints** via WebSocket (using all URLs from `app.db`)
  - Spawns MCP server subprocesses
  - Pipes messages between WebSocket and subprocess stdio
  - **Broadcasts tools to ALL connected Web Hubs**
  - Hot-reloads when config changes (including endpoint list changes)
  - Filters tools based on tool settings in `app.db`
  - Writes `tools_cache.json` for CMS to read
  - **Provides all tools to EVERY Web Hub** for browser-based testing
- **Users**: The system (runs as a background process)
- **Note**: Single source of truth for all MCP tools across the distributed system

### Data Flow Diagram (Distributed Architecture)

```
                        ┌──────────────────────────────────────────────────────────────┐
                        │                     CONFIG FILES                             │
                        │  ┌─────────────────────────────────────────────────────────┐ │
                        │  │ app.db: Multiple endpoint URLs + tool settings          │ │
                        │  │ • ws://hub1.example.com:8889                            │ │
                        │  │ • ws://hub2.example.com:8889                            │ │
                        │  │ • ws://localhost:8889 (dev)                             │ │
                        │  └──────────────────────┬──────────────────────────────────┘ │
                        │  ┌──────────────────────┴──────────────────────────────────┐ │
                        │  │ mcp_config.json: MCP server definitions                 │ │
                        │  └──────────────────────┬──────────────────────────────────┘ │
                        └─────────────────────────┼─────────────────────────────────────┘
                                                  │
                    ┌─────────────────────────────┴─────────────────────────────────┐
                    │                      web-cms/                                 │
                    │         Centralized Admin Panel (Single Instance)             │
         Writes ◄───┤              Port 8890                                        │
         Reads  ───►│    • Manages ALL Web Hub endpoint URLs                        │
                    │    • Manages MCP server configs                               │
                    └───────────────────────────────────────────────────────────────┘
                                                  ▲
                                                  │ Config only (no WS connection)
                                                  ▼
                    ┌───────────────────────────────────────────────────────────────┐
                    │                      mcp_pipe.py                              │
         Reads  ───►│         Bridge Layer (Single Instance)                        │
                    │    • Reads all endpoint URLs from app.db                      │
                    │    • Spawns MCP servers                                       │
                    └──────────┬──────────────────┬──────────────────┬──────────────┘
                               │                  │                  │
                        WebSocket (1)      WebSocket (2)      WebSocket (3)
                               │                  │                  │
           ┌───────────────────▼──────┐  ┌────────▼──────┐  ┌───────▼──────────────┐
           │  Web Hub Instance 1      │  │ Web Hub #2    │  │  Web Hub Instance N  │
           │  (Server 1)              │  │ (Server 2)    │  │  (Server N)          │
           │  ws://hub1:8889          │  │ ws://hub2:    │  │  ws://hubN:8889      │
           │  Port 8888/8889          │  │ 8889          │  │  Port 8888/8889      │
           └──────────┬───────────────┘  └───────┬───────┘  └──────────┬───────────┘
                      │                          │                     │
              ┌───────▼──────┐          ┌────────▼──────┐      ┌───────▼──────┐
              │ Browser UI 1 │          │ Browser UI 2  │      │ Browser UI N │
              │ (Region 1)   │          │ (Region 2)    │      │ (Region N)   │
              └──────────────┘          └───────────────┘      └──────────────┘
                        
                                    ▲
                                    │
                            All hubs receive
                        the same MCP tools from
                          single mcp_pipe instance
```

### Data Flow Steps (Distributed)

1. **Admin configures** via CMS → writes multiple endpoint URLs to `app.db`
2. **mcp_pipe.py reads** config files (ALL endpoint URLs, MCP servers, tool filters)
3. **mcp_pipe.py connects** to ALL Web Hub endpoints via WebSocket simultaneously
4. **mcp_pipe.py spawns** MCP server subprocesses (once for all hubs)
5. **mcp_pipe.py broadcasts** available tools to ALL connected Web Hubs
6. **Browsers connect** to their assigned/nearest Web Hub via WebSocket
7. **Web Hub forwards** tool requests from browser → mcp_pipe → MCP server
8. **mcp_pipe returns** results to the requesting Web Hub → browser
9. **Config changes** (add/remove endpoints) trigger reconnection to new endpoint list

### Real-Time Updates with Ably

The system uses **Ably** (a real-time pub/sub service) to enable instant communication between the CMS and MCP Pipe, eliminating the need for polling:

```
┌─────────────┐       ┌───────────────┐       ┌─────────────────┐
│   Web CMS   │──────▶│     Ably      │──────▶│   mcp_pipe.py   │
│ (Publisher) │       │ (Pub/Sub Hub) │       │  (Subscriber)   │
└─────────────┘       └───────────────┘       └─────────────────┘
```

| Event | Trigger | Action |
|-------|---------|--------|
| `CONNECT` | Endpoint enabled/created | MCP Pipe starts connection to endpoint |
| `DISCONNECT` | Endpoint disabled/deleted | MCP Pipe stops connection |
| `UPDATE` | Endpoint URL changed | MCP Pipe reconnects with new URL |

**Configuration**: Set `ABLY_API_KEY` in `.env` to enable real-time updates.

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
│   ├── ably_listener.py      # Ably real-time subscriber
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