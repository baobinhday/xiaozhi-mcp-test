# MCP Web Tester

A web-based interface for verifying and testing your MCP (Model Context Protocol) agent tools.

## Architecture

1. **Web Server (`web/server.py`)**: Acts as a WebSocket Hub.
2. **Web Client (`http://localhost:8888`)**: Connects to the Hub to send requests.
3. **MCP Pipe (`mcp_pipe.py`)**: Connects to the Hub to execute requests from configured MCP servers.

## Setup

### Option 1: Install with pip (Recommended)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package with dependencies
pip install -e .

# Or install with dev tools (ruff, mypy, pytest)
pip install -e ".[dev]"
```

### Option 2: Install from requirements.txt

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## Configuration

### 1. Configure Endpoints via CMS

Start the CMS server and add your WebSocket endpoints:

```bash
cd web-cms && python3 server.py
# Open http://localhost:8890 and login (default: admin/changeme)
# Add endpoint: ws://localhost:8889/mcp
```

### 2. Configure MCP Servers

```json
{
  "mcpServers": {
    "calculator": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp_server/calculator_server.py"]
    }
  }
}
```

## How to Run

### Terminal 1: Start the Web Server (Hub)

```bash
cd web
python3 server.py
```
- **Web UI:** http://localhost:8888
- **WebSocket Hub:** ws://localhost:8889

### Terminal 2: Connect MCP Tools

```bash
# Run all servers from mcp_config.json
python3 mcp_pipe.py

# Or run a specific server script
python3 mcp_pipe.py mcp_server/calculator_server.py
```

## Project Structure

```
├── src/mcp_xiaozhi/     # Core WebSocket-stdio bridge package
├── tools/               # Tool functions (calculator, search, news)
├── mcp_server/          # MCP server scripts
├── web/                 # Web interface
├── pyproject.toml       # Python project configuration
├── mcp_config.example.json  # MCP server definitions template
├── data/mcp_config.json     # MCP server definitions (gitignored)
└── mcp_pipe.py          # Entry point script
```

## Usage

1. Open http://localhost:8888 in your browser.
2. Click **Connect** (status shows "Waiting...").
3. Once Terminal 2 is running, status changes to **Connected**.
4. Use the tool forms to test your agents!
