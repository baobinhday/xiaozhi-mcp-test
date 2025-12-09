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
import json
import logging
import sys
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
import socketserver

try:
    import websockets
    from websockets.server import serve as ws_serve
except ImportError:
    import subprocess
    print("Installing websockets...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets
    from websockets.server import serve as ws_serve

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


class WebSocketHub:
    """Manages connections between browser clients and MCP tools."""
    
    def __init__(self):
        self.browser_clients = set()  # Browser UI connections
        self.mcp_tool = None          # Single MCP tool connection
        self.mcp_tool_name = None
        
    async def register_browser(self, websocket):
        """Register a browser client."""
        self.browser_clients.add(websocket)
        logger.info(f"Browser connected. Total: {len(self.browser_clients)}")
        # Send current MCP status
        await self.send_status(websocket)
        
    async def unregister_browser(self, websocket):
        """Unregister a browser client."""
        self.browser_clients.discard(websocket)
        logger.info(f"Browser disconnected. Total: {len(self.browser_clients)}")
        
    async def register_mcp(self, websocket, tool_name: str = "unknown"):
        """Register an MCP tool."""
        if self.mcp_tool:
            logger.warning("Replacing existing MCP tool connection")
            try:
                await self.mcp_tool.close()
            except:
                pass
        self.mcp_tool = websocket
        self.mcp_tool_name = tool_name
        logger.info(f"MCP tool connected: {tool_name}")
        # Notify all browsers
        await self.broadcast_status()
        
    async def unregister_mcp(self):
        """Unregister the MCP tool."""
        self.mcp_tool = None
        tool_name = self.mcp_tool_name
        self.mcp_tool_name = None
        logger.info(f"MCP tool disconnected: {tool_name}")
        # Notify all browsers
        await self.broadcast_status()
        
    async def send_status(self, websocket):
        """Send current connection status to a specific client."""
        status = {
            "type": "status",
            "mcp_connected": self.mcp_tool is not None,
            "mcp_tool_name": self.mcp_tool_name
        }
        try:
            await websocket.send(json.dumps(status))
        except:
            pass
            
    async def broadcast_status(self):
        """Broadcast connection status to all browser clients."""
        for client in self.browser_clients.copy():
            await self.send_status(client)
            
    async def forward_to_mcp(self, message: str) -> bool:
        """Forward a message from browser to MCP tool."""
        if not self.mcp_tool:
            return False
        try:
            await self.mcp_tool.send(message)
            return True
        except Exception as e:
            logger.error(f"Error forwarding to MCP: {e}")
            return False
            
    async def forward_to_browsers(self, message: str):
        """Forward a message from MCP tool to all browser clients."""
        for client in self.browser_clients.copy():
            try:
                await client.send(message)
            except:
                pass


# Global hub instance
hub = WebSocketHub()


async def handle_connection(websocket, path):
    """Handle incoming WebSocket connections."""
    # Determine client type from path or first message
    # /browser = browser client
    # /mcp = MCP tool
    
    client_type = None
    
    if path == "/mcp" or path.startswith("/mcp"):
        client_type = "mcp"
        # Extract tool name from query string if present
        tool_name = "unknown"
        if "?" in path:
            params = dict(p.split("=") for p in path.split("?")[1].split("&") if "=" in p)
            tool_name = params.get("tool", "unknown")
        await hub.register_mcp(websocket, tool_name)
        
        try:
            async for message in websocket:
                logger.debug(f"MCP → Browser: {message[:100]}...")
                await hub.forward_to_browsers(message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await hub.unregister_mcp()
            
    else:  # Default to browser client
        client_type = "browser"
        await hub.register_browser(websocket)
        
        try:
            async for message in websocket:
                logger.debug(f"Browser → MCP: {message[:100]}...")
                success = await hub.forward_to_mcp(message)
                if not success:
                    # Send error back to browser
                    error = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32000,
                            "message": "MCP tool not connected"
                        }
                    }
                    await websocket.send(json.dumps(error))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await hub.unregister_browser(websocket)


async def run_websocket_server():
    """Run the WebSocket hub server."""
    async with ws_serve(handle_connection, "0.0.0.0", WS_PORT):
        logger.info(f"WebSocket hub running on ws://localhost:{WS_PORT}")
        await asyncio.Future()  # Run forever


def run_http_server():
    """Run HTTP server for static files (blocking)."""
    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(WEB_DIR), **kwargs)
            
        def log_message(self, format, *args):
            if "GET / " in args[0] or "GET /style" in args[0] or "GET /app" in args[0]:
                logger.info(f"[HTTP] {args[0]}")
            
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()
    
    class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        
    server = ThreadedServer(("0.0.0.0", HTTP_PORT), QuietHandler)
    logger.info(f"HTTP server running on http://localhost:{HTTP_PORT}")
    server.serve_forever()


async def main():
    """Main entry point."""
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║              MCP Web Tester - WebSocket Hub                       ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  HTTP Server:       http://localhost:{HTTP_PORT:<5}                      ║
║  WebSocket Hub:     ws://localhost:{WS_PORT:<5}                        ║
║                                                                   ║
║  Usage:                                                           ║
║    1. Open http://localhost:{HTTP_PORT} in browser                      ║
║    2. Connect MCP tool using mcp_pipe.py:                         ║
║       MCP_ENDPOINT=ws://localhost:{WS_PORT}/mcp python3 mcp_pipe.py      ║
║    3. Web UI will show "Connected" when tool joins                ║
║                                                                   ║
║  Press Ctrl+C to stop.                                            ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Run HTTP server in a thread
    import threading
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Run WebSocket server
    await run_websocket_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")
