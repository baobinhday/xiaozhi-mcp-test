# MCP Web Tester

A web-based interface for verifying and testing your MCP (Model Context Protocol) agent tools.

## Architecture

1. **Web Server (`web/server.py`)**: Acts as a WebSocket Hub.
2. **Web Client (`http://localhost:8888`)**: Connects to the Hub to send requests.
3. **MCP Tool (`mcp_pipe.py`)**: Connects to the Hub to execute requests.

## Setup

1.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip3 install -r requirements.txt
    ```

## Configuration

The application is configured to handle environment variables flexibly for both Development and Docker environments:

*   **Development**: Create a `.env` file (copy from `.env.example`). Variables in this file will be loaded automatically.
*   **Docker**: Use standard OS environment variables (e.g., `docker run -e MCP_ENDPOINT=...`). These take precedence and are respected.

**Example `.env`:**
```bash
MCP_ENDPOINT=ws://localhost:8889/mcp
```

## How to Run

You need to run two separate terminal commands:

### Terminal 1: Start the Web Server (Hub)

This starts the web UI and the WebSocket server.

```bash
# From the project root
cd web
python3 server.py
```
*   **Web UI:** http://localhost:8888
*   **WebSocket Hub:** ws://localhost:8889

### Terminal 2: Connect Your MCP Tool

This connects your Python MCP tool to the Web Server's hub using `mcp_pipe.py`.

```bash
# From the project root
export MCP_ENDPOINT=ws://localhost:8889/mcp
python3 mcp_pipe.py tools/agent_tools.py
```

*Note: You can replace `tools/agent_tools.py` with any text-based MCP tool script (e.g., `tools/calculator.py`).*

## Usage

1. Open http://localhost:8888 in your browser.
2. Click **Connect** (The status should change to "Waiting...").
3. Once Terminal 2 is running, the status will change to **Connected**.
4. Use the tool forms to test your agents!
