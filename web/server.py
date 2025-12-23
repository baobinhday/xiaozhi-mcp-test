#!/usr/bin/env python3
"""
MCP Web Tester Server - WebSocket Hub.
Hosts WebSocket server that bridges browser UI and MCP tools.

Usage:
    python3 server.py [http_port] [ws_port]
    
    Default: HTTP on 8888, WebSocket on 8889

The web UI connects to receive/send messages.
MCP tools connect to provide tool execution.
"""

import asyncio
import logging
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=False)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MCP_HUB')

# Configuration
HTTP_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
WS_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8889
WEB_DIR = Path(__file__).parent.absolute()

# Import modules after dotenv loads
from auth import WEB_USERNAME, WEB_PASSWORD
from http_handler import run_http_server
from websocket_hub import run_websocket_server


async def main():
    """Main entry point."""
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║              MCP Web Tester - WebSocket Hub                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  HTTP Server:       http://localhost:{HTTP_PORT:<5}              ║
║  WebSocket Hub:     ws://localhost:{WS_PORT:<5}                  ║
║                                                                  ║
║  Authentication:                                                 ║
║    Username: {WEB_USERNAME:<20}                             ║
║    Password: {'*' * min(len(WEB_PASSWORD), 10):<20}                             ║
║                                                                  ║
║  Set WEB_USERNAME, WEB_PASSWORD in .env to change                ║
║                                                                  ║
║  Usage:                                                          ║
║    1. Open http://localhost:{HTTP_PORT} in browser               ║
║    2. Login with credentials above                               ║
║    3. Add endpoint via CMS at http://localhost:8890              ║
║    4. Endpoint local: ws://localhost:{WS_PORT}/mcp               ║
║    5. Run MCP tools: python3 mcp_pipe.py                         ║
║    6. Web UI will show "Connected" when tool joins               ║
║                                                                  ║
║  Press Ctrl+C to stop.                                           ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Run HTTP server in a thread
    http_thread = threading.Thread(
        target=run_http_server, 
        args=(HTTP_PORT, WEB_DIR), 
        daemon=True
    )
    http_thread.start()
    
    # Run WebSocket server
    await run_websocket_server(WS_PORT)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")
