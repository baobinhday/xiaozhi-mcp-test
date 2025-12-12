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
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
import socketserver
from urllib.parse import urlparse

from dotenv import load_dotenv

try:
    import websockets
    from websockets.server import serve as ws_serve
except ImportError:
    import subprocess
    print("Installing websockets...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets
    from websockets.server import serve as ws_serve

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

# Authentication settings
WEB_USERNAME = os.environ.get("WEB_USERNAME", "admin")
WEB_PASSWORD = os.environ.get("WEB_PASSWORD", "admin1asdasdfsdafdsg$####43dgsdg23")
WEB_SECRET_KEY = os.environ.get("WEB_SECRET_KEY", secrets.token_hex(32))
SESSION_DURATION_HOURS = 24

# In-memory session storage
sessions = {}


def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)



def create_session(username: str) -> str:
    """Create a new session for a user."""
    token = generate_session_token()
    sessions[token] = {
        "username": username,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)
    }
    return token


def validate_session(token: str) -> bool:
    """Validate a session token."""
    if not token or token not in sessions:
        return False
    
    session = sessions[token]
    if datetime.now(timezone.utc) > session["expires_at"]:
        del sessions[token]
        return False
    
    return True


def destroy_session(token: str) -> bool:
    """Destroy a session."""
    if token in sessions:
        del sessions[token]
        return True
    return False


class WebSocketHub:
    """Manages connections between browser clients and MCP tools."""
    
    def __init__(self):
        self.browser_clients = set()  # Browser UI connections
        self.mcp_tools = {}           # Dict: server_name -> websocket
        self.server_tools = {}        # Dict: server_name -> list of tools
        self.tool_registry = {}       # Dict: tool_name -> server_name (for routing)
        self.pending_inits = set()    # Track servers waiting for initialize response
        self.pending_tools_requests = {}  # Dict: request_id -> asyncio.Event for refresh
        
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
        
    async def register_mcp(self, websocket, server_name: str = "unknown"):
        """Register an MCP tool."""
        self.mcp_tools[server_name] = websocket
        self.server_tools[server_name] = []  # Will be populated when tools/list response arrives
        self.pending_inits.add(server_name)  # Track that we're waiting for init response
        logger.info(f"MCP server connected: {server_name}")
        
        # Initialize the MCP server
        try:
            init_request = {
                "jsonrpc": "2.0",
                "id": f"hub_init_{server_name}",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "MCP Hub",
                        "version": "1.0.0"
                    }
                }
            }
            await websocket.send(json.dumps(init_request))
            logger.info(f"Sent initialize request to server '{server_name}'")
            # Will request tools when we receive the initialize response
        except Exception as e:
            logger.error(f"Failed to send initialize to '{server_name}': {e}")
            self.pending_inits.discard(server_name)
        
        # Notify all browsers
        await self.broadcast_status()
        
    async def unregister_mcp(self, server_name: str):
        """Unregister an MCP tool."""
        if server_name in self.mcp_tools:
            del self.mcp_tools[server_name]
        if server_name in self.server_tools:
            # Remove tools from registry
            for tool in self.server_tools[server_name]:
                tool_name = tool.get("name")
                if tool_name and self.tool_registry.get(tool_name) == server_name:
                    del self.tool_registry[tool_name]
            del self.server_tools[server_name]
        logger.info(f"MCP server disconnected: {server_name}")
        # Notify all browsers
        await self.broadcast_status()
        
    async def send_status(self, websocket):
        """Send current connection status to a specific client."""
        status = {
            "type": "status",
            "mcp_connected": len(self.mcp_tools) > 0,
            "mcp_servers": list(self.mcp_tools.keys())
        }
        try:
            await websocket.send(json.dumps(status))
        except:
            pass
            
    async def broadcast_status(self):
        """Broadcast connection status to all browser clients."""
        for client in self.browser_clients.copy():
            await self.send_status(client)
    
    async def refresh_all_tools(self, timeout: float = 3.0):
        """Request fresh tools from all MCP servers.
        
        This clears the current cache and requests tools/list from each server,
        so the bridge will apply the latest filter from tools_config.json.
        """
        if not self.mcp_tools:
            return
        
        # Clear current cache to force fresh data
        self.server_tools.clear()
        self.tool_registry.clear()
        
        # Create events for each server to track responses
        import asyncio
        events = {}
        
        for server_name in list(self.mcp_tools.keys()):
            request_id = f"refresh_tools_{server_name}_{id(self)}"
            events[server_name] = asyncio.Event()
            self.pending_tools_requests[request_id] = (server_name, events[server_name])
            
            try:
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "tools/list",
                    "params": {}
                }
                await self.mcp_tools[server_name].send(json.dumps(tools_request))
                logger.info(f"Requested tools refresh from '{server_name}'")
            except Exception as e:
                logger.error(f"Failed to request tools from '{server_name}': {e}")
                events[server_name].set()  # Mark as done to not block
        
        # Wait for all responses with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*[event.wait() for event in events.values()]),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for tools refresh responses")
        
        # Clean up pending requests
        for request_id in list(self.pending_tools_requests.keys()):
            if request_id.startswith("refresh_tools_"):
                del self.pending_tools_requests[request_id]
            
            
    async def forward_to_mcp(self, message: str, server_name: str = None) -> bool:
        """Forward a message from browser to specific MCP tool or broadcast to all."""
        if not self.mcp_tools:
            return False
        
        # If server_name is specified, route to that server
        if server_name:
            if server_name not in self.mcp_tools:
                logger.error(f"Server '{server_name}' not found")
                return False
            try:
                await self.mcp_tools[server_name].send(message)
                return True
            except Exception as e:
                logger.error(f"Error forwarding to {server_name}: {e}")
                return False
        
        # Otherwise, broadcast to all MCP servers (for initialize, etc.)
        success = False
        for name, websocket in self.mcp_tools.items():
            try:
                await websocket.send(message)
                success = True
            except Exception as e:
                logger.error(f"Error forwarding to {name}: {e}")
        return success
            
    async def forward_to_browsers(self, message: str):
        """Forward a message from MCP tool to all browser clients."""
        for client in self.browser_clients.copy():
            try:
                await client.send(message)
            except:
                pass
    
    async def handle_browser_message(self, message: str, websocket) -> bool:
        """Intercept and handle browser messages. Returns True if handled, False otherwise."""
        try:
            msg = json.loads(message)
            method = msg.get("method")
            request_id = msg.get("id")
            
            # Intercept initialize - don't forward to MCP servers as they're already initialized
            if method == "initialize":
                logger.info("Intercepting initialize request from browser")
                # Return a successful initialize response
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "serverInfo": {
                            "name": "MCP Hub",
                            "version": "1.0.0"
                        }
                    }
                }
                await websocket.send(json.dumps(response))
                logger.info("Sent initialize response to browser")
                return True
            
            # Intercept notifications/initialized - browser acknowledgment, don't forward
            elif method == "notifications/initialized":
                logger.info("Browser sent initialized notification")
                return True  # Don't forward this
            
            # Intercept tools/list to get fresh tools from all servers
            # Hub requests fresh tools from each MCP server -> bridge applies latest filter
            elif method == "tools/list":
                logger.info("Intercepting tools/list request - refreshing from all servers")
                # Refresh tools from all MCP servers to get latest filter state
                await self.refresh_all_tools(timeout=3.0)
                tools = self.get_cached_aggregated_tools()
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools}
                }
                await websocket.send(json.dumps(response))
                logger.info(f"Returned {len(tools)} aggregated tools to browser")
                return True
            
            # Intercept tools/call to route to correct server
            elif method == "tools/call":
                tool_name = msg.get("params", {}).get("name")
                if tool_name:
                    server_name = self.tool_registry.get(tool_name)
                    if server_name:
                        logger.info(f"Routing tools/call for '{tool_name}' to server '{server_name}'")
                        return await self.forward_to_mcp(message, server_name)
                    else:
                        logger.warning(f"Tool '{tool_name}' not found in registry")
                        error = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Tool '{tool_name}' not found"
                            }
                        }
                        await websocket.send(json.dumps(error))
                        return True
            
            # Other messages: broadcast to all servers
            return False
            
        except json.JSONDecodeError:
            return False
    
    async def handle_mcp_message(self, message: str, server_name: str):
        """Intercept and cache MCP server responses, especially initialize and tools/list."""
        try:
            # Try to parse as JSON
            msg = json.loads(message)
            msg_id = msg.get("id", "")
            logger.info(f"[{server_name}] Parsed message ID: {msg_id}, has result: {'result' in msg}, has tools: {'tools' in msg.get('result', {})}")
            
            # Check if this is an initialize response
            if msg_id == f"hub_init_{server_name}" and "result" in msg:
                logger.info(f"Received initialize response from '{server_name}'")
                self.pending_inits.discard(server_name)
                
                # Send initialized notification (required by MCP protocol)
                try:
                    initialized_notification = {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                        "params": {}
                    }
                    if server_name in self.mcp_tools:
                        await self.mcp_tools[server_name].send(json.dumps(initialized_notification))
                        logger.info(f"Sent initialized notification to '{server_name}'")
                except Exception as e:
                    logger.error(f"Failed to send initialized notification to '{server_name}': {e}")
                
                # Now request tools from this server
                try:
                    tools_request = {
                        "jsonrpc": "2.0",
                        "id": f"hub_tools_{server_name}",
                        "method": "tools/list",
                        "params": {}
                    }
                    if server_name in self.mcp_tools:
                        await self.mcp_tools[server_name].send(json.dumps(tools_request))
                        logger.info(f"Requested tools from initialized server '{server_name}'")
                except Exception as e:
                    logger.error(f"Failed to request tools from '{server_name}': {e}")
            
            # Check if this is a tools/list response
            elif "result" in msg and "tools" in msg.get("result", {}):
                tools = msg["result"]["tools"]
                self.server_tools[server_name] = tools
                logger.info(f"✓ Cached {len(tools)} tools from server '{server_name}'")
                
                # Update tool registry for routing
                for tool in tools:
                    tool_name = tool.get("name")
                    if tool_name:
                        self.tool_registry[tool_name] = server_name
                        logger.info(f"  - Registered tool '{tool_name}' from '{server_name}'")
                
                # Check if this is a response to a refresh request
                request_id = msg.get("id", "")
                if request_id in self.pending_tools_requests:
                    _, event = self.pending_tools_requests[request_id]
                    event.set()  # Signal that this server has responded
            else:
                logger.debug(f"Message from {server_name} is not a tools/list response")
                        
        except (json.JSONDecodeError, KeyError) as e:
            # Silently ignore non-JSON messages (debug output, logs, etc.)
            logger.debug(f"Non-JSON or invalid message from {server_name}: {str(e)}")
            pass
    
    def get_cached_aggregated_tools(self) -> list:
        """Return aggregated tools from cache with conflict resolution.
        
        Hub is a pure pass-through: bridge handles all filtering and custom metadata.
        This method only aggregates tools from multiple servers and handles name conflicts.
        """
        all_tools = []
        tool_names_seen = set()
        
        for server_name, tools in self.server_tools.items():
            for tool in tools:
                tool_name = tool.get("name")
                if not tool_name:
                    continue
                
                # Create a copy to avoid modifying the cached tool
                tool_copy = tool.copy()
                
                # Handle name conflicts: prefix with server name
                if tool_name in tool_names_seen:
                    prefixed_name = f"{server_name}.{tool_name}"
                    logger.info(f"Tool name conflict: renaming '{tool_name}' to '{prefixed_name}'")
                    tool_copy["name"] = prefixed_name
                    tool_copy["description"] = f"[{server_name}] {tool.get('description', '')}"
                    self.tool_registry[prefixed_name] = server_name
                else:
                    # Add server info to description
                    tool_copy["description"] = f"[{server_name}] {tool.get('description', '')}"
                    self.tool_registry[tool_name] = server_name
                    tool_names_seen.add(tool_name)
                
                all_tools.append(tool_copy)
        
        return all_tools


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
    elif "?" in path and "server=" in path:
         # Fallback: Check if it's an MCP tool via query param even if path is wrong
        client_type = "mcp"
    
    if client_type == "mcp":
        # Extract server name from query string
        server_name = "unknown"
        if "?" in path:
            params = dict(p.split("=") for p in path.split("?")[1].split("&") if "=" in p)
            server_name = params.get("server", "unknown")
        await hub.register_mcp(websocket, server_name)
        
        try:
            async for message in websocket:
                logger.info(f"MCP({server_name}) → Hub: {message[:150]}...")
                # Intercept and cache MCP responses (especially tools/list)
                await hub.handle_mcp_message(message, server_name)
                # Forward to all browsers
                await hub.forward_to_browsers(message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await hub.unregister_mcp(server_name)
            
    else:  # Default to browser client
        client_type = "browser"
        await hub.register_browser(websocket)
        
        try:
            async for message in websocket:
                logger.debug(f"Browser → MCP: {message[:100]}...")
                # Try to handle message (intercept tools/list and tools/call)
                handled = await hub.handle_browser_message(message, websocket)
                if handled:
                    continue
                
                # Otherwise forward to all MCP servers
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
    """Run HTTP server for static files with authentication (blocking)."""
    
    class AuthHandler(SimpleHTTPRequestHandler):
        """HTTP handler with session-based authentication."""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(WEB_DIR), **kwargs)
        
        def log_message(self, format, *args):
            # Skip logging certain requests or handle errors
            if args and isinstance(args[0], str):
                if "GET / " in args[0] or "GET /style" in args[0] or "GET /app" in args[0]:
                    logger.info(f"[HTTP] {args[0]}")
        
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()
        
        def send_json_response(self, data: dict, status: int = 200):
            """Send a JSON response."""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        
        def get_session_token(self) -> str:
            """Extract session token from cookies."""
            cookie_header = self.headers.get("Cookie", "")
            for cookie in cookie_header.split(";"):
                cookie = cookie.strip()
                if cookie.startswith("web_session="):
                    return cookie[12:]
            return ""
        
        def is_authenticated(self) -> bool:
            """Check if the request is authenticated."""
            token = self.get_session_token()
            return validate_session(token)
        
        def read_body(self) -> dict:
            """Read and parse JSON body."""
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                return {}
            body = self.rfile.read(content_length)
            return json.loads(body.decode())
        
        def do_OPTIONS(self):
            """Handle CORS preflight requests."""
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
        
        def do_GET(self):
            """Handle GET requests."""
            parsed = urlparse(self.path)
            path = parsed.path
            
            # API routes (no auth required)
            if path == "/api/auth/check":
                is_auth = self.is_authenticated()
                self.send_json_response({"authenticated": is_auth})
                return
            
            # API route to get endpoints (requires auth)
            if path == "/api/endpoints":
                if not self.is_authenticated():
                    self.send_json_response({"error": "Unauthorized"}, 401)
                    return
                try:
                    # Import database module
                    sys.path.insert(0, str(Path(__file__).parent.parent))
                    from src.mcp_xiaozhi.database import get_enabled_endpoints, init_db
                    init_db()
                    endpoints = get_enabled_endpoints()
                    self.send_json_response({"endpoints": endpoints})
                except Exception as e:
                    logger.error(f"Failed to fetch endpoints: {e}")
                    self.send_json_response({"error": str(e)}, 500)
                return
            
            # Protected static files - redirect to login if not authenticated
            # Allow CSS, JS, and fonts without auth for login page styling
            allowed_without_auth = [
                '/style.css', '/common.css', '/app.js', 
                '/js/', '/login.html'
            ]
            
            needs_auth = True
            for allowed in allowed_without_auth:
                if path.startswith(allowed) or path == allowed:
                    needs_auth = False
                    break
            
            if needs_auth and not self.is_authenticated():
                # For root path, still serve index.html (it will show login)
                if path == "/" or path == "":
                    self.path = "/index.html"
                    super().do_GET()
                    return
                # For other paths, return 401
                self.send_json_response({"error": "Unauthorized"}, 401)
                return
            
            # Serve static files
            if path == "/" or path == "":
                self.path = "/index.html"
            super().do_GET()
        
        def do_POST(self):
            """Handle POST requests."""
            parsed = urlparse(self.path)
            path = parsed.path
            
            if path == "/api/login":
                body = self.read_body()
                username = body.get("username", "")
                password = body.get("password", "")
                
                if username == WEB_USERNAME and password == WEB_PASSWORD:
                    token = create_session(username)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Set-Cookie", f"web_session={token}; Path=/; HttpOnly; Max-Age={SESSION_DURATION_HOURS * 3600}")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "message": "Login successful"}).encode())
                else:
                    self.send_json_response({"error": "Invalid credentials"}, 401)
            
            elif path == "/api/logout":
                token = self.get_session_token()
                destroy_session(token)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie", "web_session=; Path=/; HttpOnly; Max-Age=0")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
            
            else:
                self.send_json_response({"error": "Not found"}, 404)
    
    class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        
    server = ThreadedServer(("0.0.0.0", HTTP_PORT), AuthHandler)
    logger.info(f"HTTP server running on http://localhost:{HTTP_PORT}")
    server.serve_forever()


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
