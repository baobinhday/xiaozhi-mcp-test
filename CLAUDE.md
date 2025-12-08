# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Project Overview

This project (`mcp-xiaozhi`) serves as a bridge for integrating local Python-based agent tools with a larger ecosystem, likely a Multi-Agent Communication Protocol (MCP) server. It leverages WebSockets for communication and `stdio` for interacting with local processes. The core functionality revolves around the `mcp_pipe.py` script, which manages connections and process I/O, and `agent_tools.py`, which defines specific agent capabilities.

## Architecture

The project architecture consists of two main Python components:

1.  **`mcp_pipe.py`**: This script acts as a robust WebSocket-to-stdio pipe. Its responsibilities include:
    *   Connecting to a specified MCP WebSocket endpoint (`MCP_ENDPOINT`).
    *   Managing local Python processes (agent tools).
    *   Piping `stdin`, `stdout`, and `stderr` between the WebSocket connection and the local processes.
    *   Implementing reconnection logic with exponential backoff for resilience.
    *   Loading configuration from `.env` (for `MCP_ENDPOINT`) and optionally `mcp_config.json` for defining multiple MCP servers and their execution commands.

2.  **`agent_tools.py`**: This script defines the actual functionalities (tools) that the agent provides. It uses the `FastMCP` framework (imported from `mcp.server.fastmcp`) to expose these tools. Currently, it includes:
    *   `tim_kiem_web`: A web search tool utilizing DuckDuckGo (`ddgs` library) for querying information.
    *   `doc_tin_tuc_moi_nhat`: A news aggregation tool that fetches the latest news from prominent Vietnamese news sources via RSS feeds (`feedparser` library).
    *   It communicates via `stdio`, which `mcp_pipe.py` then handles for WebSocket transport.

## Data Flow

1.  The `mcp_pipe.py` script starts, reads the `MCP_ENDPOINT` from the environment, and then either launches a specified agent script (like `agent_tools.py`) or all configured agents from `mcp_config.json`.
2.  `mcp_pipe.py` establishes a WebSocket connection to the `MCP_ENDPOINT`.
3.  Concurrently, `mcp_pipe.py` starts the local agent process(es) (e.g., `agent_tools.py`) and redirects their `stdin`, `stdout`, and `stderr`.
4.  Messages from the MCP WebSocket server are piped to the `stdin` of the local agent process.
5.  Output from the `stdout` of the local agent process is sent back to the MCP WebSocket server.
6.  `stderr` from the local agent process is printed to the terminal where `mcp_pipe.py` is running, aiding in debugging.

## Setup and Running

### Prerequisites

*   Python 3.x
*   `pip` (Python package installer)
*   `git` (for cloning the repository)
*   `ffmpeg`, `libsdl2-dev`, `libsdl2-image-dev`, `libsdl2-mixer-dev`, `libsdl2-ttf-dev` (These seem to be dependencies for a broader system, possibly related to `xiaozhi`'s multimedia capabilities, though not directly used by `agent_tools.py` itself).

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/thanhtantran/mcp-server-xiaozhi # Or the specific repository
    cd mcp-server-xiaozhi # Or your project directory
    ```

2.  **Install system dependencies (if needed):**
    ```bash
    sudo apt install -y python3 python3-pip git ffmpeg libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
    ```
    *(Note: These dependencies might be for other parts of the "xiaozhi" project and not strictly for `mcp_pipe.py` or `agent_tools.py`.)*

3.  **Create a `.env` file:**
    Create a file named `.env` in the project root and add your MCP WebSocket endpoint:
    ```
    MCP_ENDPOINT="wss://your-mcp-server-endpoint.com/ws"
    ```
    Replace `"wss://your-mcp-server-endpoint.com/ws"` with the actual WebSocket URL of your MCP server.

4.  **Install Python dependencies:**
    ```bash
    pip3 install -r requirements.txt
    ```

### Running the Agent

To start the `agent_tools.py` as an MCP service, run `mcp_pipe.py` with `agent_tools.py` as an argument:

```bash
python3 mcp_pipe.py agent_tools.py
```

This command will:
1.  Connect to the `MCP_ENDPOINT` specified in your `.env` file.
2.  Launch `agent_tools.py` as a subprocess.
3.  Pipe communication between the MCP WebSocket server and `agent_tools.py`'s `stdio`.

## Development Commands

### Running tests
```bash
# There is a test calculator tool in test/calculator.py that can be used for testing
python3 test/calculator.py
```

### Running with configuration file
```bash
# Run with mcp_config.json (if available)
python3 mcp_pipe.py
```

### Running specific agent tools
```bash
# Run a single local server script
python3 mcp_pipe.py path/to/server.py
```

## Extending Functionality

New tools can be added to `agent_tools.py` by defining functions and decorating them with `@mcp.tool()`. These tools will then be automatically exposed through the `FastMCP` server when `agent_tools.py` is run via `mcp_pipe.py`.

## Configuration Options

The system supports configuration through:
1. Environment variables (`.env` file)
2. Optional `mcp_config.json` file for defining multiple MCP servers and their execution commands

Configuration priority:
- If target matches a server in config.mcpServers: use its definition
- Else: treat target as a Python script path (back-compat)

## Development Workflow

1.  **Define new tools** in `agent_tools.py` (or a similar script).
2.  **Ensure `MCP_ENDPOINT` is configured** in `.env`.
3.  **Run `mcp_pipe.py`** pointing to your agent script to test and deploy.
4.  **Monitor logs** from `mcp_pipe.py` for connection status and any `stderr` output from your agent tools.

## Project Structure

- `mcp_pipe.py`: Main WebSocket-to-stdio bridge with reconnection logic
- `agent_tools.py`: Defines the agent's capabilities and tools
- `requirements.txt`: Python dependencies
- `test/calculator.py`: Example test calculator tool
- `.env.local`: Environment variables including MCP_ENDPOINT
- `Readme.md`: Basic setup instructions