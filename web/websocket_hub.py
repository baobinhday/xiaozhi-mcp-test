"""
WebSocket Hub for MCP Web Tester.
Manages connections between browser clients and MCP tools.
"""

import asyncio
import json
import logging
import sys

try:
    import websockets
    from websockets.server import serve as ws_serve
except ImportError:
    import subprocess
    print("Installing websockets...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets
    from websockets.server import serve as ws_serve

from auth import MCP_WS_TOKEN

logger = logging.getLogger('MCP_HUB')


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
    # Extract query parameters
    params = {}
    if "?" in path:
        try:
            params = dict(p.split("=") for p in path.split("?")[1].split("&") if "=" in p)
        except ValueError:
            pass
    
    # Debug logging
    logger.info(f"WebSocket connection: path='{path}', params={params}")
    
    # Determine client type from path
    # /browser = browser client
    # /mcp = MCP tool
    
    client_type = None
    base_path = path.split("?")[0]
    
    if base_path == "/mcp" or base_path.startswith("/mcp"):
        client_type = "mcp"
    elif "server" in params:
        # Fallback: Check if it's an MCP tool via query param
        client_type = "mcp"
    
    if client_type == "mcp":
        server_name = params.get("server", "unknown")
        
        # Validate token if MCP_WS_TOKEN is configured
        if MCP_WS_TOKEN:
            provided_token = params.get("token", "")
            if provided_token != MCP_WS_TOKEN:
                logger.warning(f"MCP connection rejected: invalid token from server '{server_name}'")
                await websocket.close(4001, "Invalid or missing token")
                return
            logger.info(f"MCP connection token validated for server '{server_name}'")
        
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
        
        # No authentication required for WebSocket browser clients
        # (matches Xiaozhi model where ESP32 agent connects directly to Broker)
        
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


async def run_websocket_server(ws_port: int):
    """Run the WebSocket hub server."""
    async with ws_serve(handle_connection, "0.0.0.0", ws_port):
        logger.info(f"WebSocket hub running on ws://localhost:{ws_port}")
        await asyncio.Future()  # Run forever
