#!/usr/bin/env python3
"""
MCP Endpoints CMS - Web admin interface for managing MCP endpoints.

Usage:
    python3 server.py [port]
    
    Default: HTTP on 8890
"""

import hashlib
import json
import logging
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from functools import wraps
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.mcp_xiaozhi.database import (
    add_endpoint,
    delete_endpoint,
    get_all_endpoints,
    get_connection,
    get_endpoint_by_id,
    init_db,
    update_endpoint,
)

# Load environment variables
load_dotenv(override=False)

# Configuration
HTTP_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8890
CMS_DIR = Path(__file__).parent.absolute()

# Authentication settings
CMS_USERNAME = os.environ.get("CMS_USERNAME", "admin")
CMS_PASSWORD = os.environ.get("CMS_PASSWORD", "asfadfdagdfhfghjgjghkj23546%354")
CMS_SECRET_KEY = os.environ.get("CMS_SECRET_KEY", secrets.token_hex(32))
SESSION_DURATION_HOURS = 24

# In-memory session storage (simple implementation)
sessions = {}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('CMS')

# MCP Config file path
MCP_CONFIG_PATH = Path(__file__).parent.parent / "data" / "mcp_config.json"

# Tools config file path (for enabling/disabling individual tools)
TOOLS_CONFIG_PATH = Path(__file__).parent.parent / "data" / "tools_config.json"

# Tools cache file path (cached tools from bridge, for CMS)
TOOLS_CACHE_PATH = Path(__file__).parent.parent / "data" / "tools_cache.json"


def load_mcp_config() -> dict:
    """Load MCP config from mcp_config.json."""
    try:
        if MCP_CONFIG_PATH.exists():
            with open(MCP_CONFIG_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading mcp_config.json: {e}")
    return {"mcpServers": {}}


def save_mcp_config(config: dict) -> bool:
    """Save MCP config to mcp_config.json."""
    try:
        with open(MCP_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving mcp_config.json: {e}")
        return False


def load_tools_config() -> dict:
    """Load tools config from tools_config.json."""
    try:
        if TOOLS_CONFIG_PATH.exists():
            with open(TOOLS_CONFIG_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading tools_config.json: {e}")
    return {"disabledTools": {}}


def save_tools_config(config: dict) -> bool:
    """Save tools config to tools_config.json."""
    try:
        # Ensure data directory exists
        TOOLS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOOLS_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving tools_config.json: {e}")
        return False


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


class CMSHandler(SimpleHTTPRequestHandler):
    """HTTP handler for CMS requests."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(CMS_DIR), **kwargs)
    
    def log_message(self, format, *args):
        """Custom log formatting."""
        logger.info(f"{self.address_string()} - {format % args}")
    
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
            if cookie.startswith("session="):
                return cookie[8:]
        return ""
    
    def is_authenticated(self) -> bool:
        """Check if the request is authenticated."""
        token = self.get_session_token()
        return validate_session(token)
    
    def require_auth(self) -> bool:
        """Check authentication and send 401 if not authenticated."""
        if not self.is_authenticated():
            self.send_json_response({"error": "Unauthorized"}, 401)
            return False
        return True
    
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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # API routes
        if path == "/api/endpoints":
            if not self.require_auth():
                return
            endpoints = get_all_endpoints()
            self.send_json_response({"endpoints": endpoints})
        
        elif path == "/api/auth/check":
            is_auth = self.is_authenticated()
            self.send_json_response({"authenticated": is_auth})
        
        elif path == "/api/backup":
            if not self.require_auth():
                return
            endpoints = get_all_endpoints()
            backup_data = {
                "version": "1.0",
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "endpoints": endpoints
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition", "attachment; filename=mcp_endpoints_backup.json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(backup_data, indent=2).encode())
        
        elif path.startswith("/api/endpoints/"):
            if not self.require_auth():
                return
            try:
                endpoint_id = int(path.split("/")[-1])
                endpoint = get_endpoint_by_id(endpoint_id)
                if endpoint:
                    self.send_json_response(endpoint)
                else:
                    self.send_json_response({"error": "Not found"}, 404)
            except ValueError:
                self.send_json_response({"error": "Invalid ID"}, 400)
        
        elif path == "/api/mcp-servers":
            if not self.require_auth():
                return
            config = load_mcp_config()
            servers = []
            for name, server in config.get("mcpServers", {}).items():
                servers.append({
                    "name": name,
                    "type": server.get("type", "stdio"),
                    "command": server.get("command", ""),
                    "args": server.get("args", []),
                    "env": server.get("env", {}),
                    "url": server.get("url", ""),
                    "headers": server.get("headers", {}),
                    "disabled": server.get("disabled", False)
                })
            self.send_json_response({"servers": servers})
        
        elif path == "/api/mcp-config/backup":
            if not self.require_auth():
                return
            config = load_mcp_config()
            backup_data = {
                "version": "1.0",
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "mcpServers": config.get("mcpServers", {})
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition", "attachment; filename=mcp_config_backup.json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(backup_data, indent=2).encode())
        
        elif path == "/api/mcp-tools":
            if not self.require_auth():
                return
            # Get tools config for disabled tools and custom metadata
            tools_config = load_tools_config()
            disabled_tools = tools_config.get("disabledTools", {})
            custom_tools = tools_config.get("customTools", {})
            self.send_json_response({
                "disabledTools": disabled_tools,
                "customTools": custom_tools
            })
        
        elif path == "/api/mcp-tools/cache":
            if not self.require_auth():
                return
            # Get cached tools list from bridge (unfiltered, all tools)
            try:
                if TOOLS_CACHE_PATH.exists():
                    with open(TOOLS_CACHE_PATH, 'r') as f:
                        tools_cache = json.load(f)
                    self.send_json_response({"tools": tools_cache})
                else:
                    self.send_json_response({"tools": {}})
            except Exception as e:
                logger.error(f"Error reading tools cache: {e}")
                self.send_json_response({"tools": {}})
        
        else:
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
            
            if username == CMS_USERNAME and password == CMS_PASSWORD:
                token = create_session(username)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie", f"session={token}; Path=/; HttpOnly; Max-Age={SESSION_DURATION_HOURS * 3600}")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "message": "Login successful"}).encode())
            else:
                self.send_json_response({"error": "Invalid credentials"}, 401)
        
        elif path == "/api/logout":
            token = self.get_session_token()
            destroy_session(token)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", "session=; Path=/; HttpOnly; Max-Age=0")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode())
        
        elif path == "/api/endpoints":
            if not self.require_auth():
                return
            body = self.read_body()
            name = body.get("name", "").strip()
            url = body.get("url", "").strip()
            enabled = body.get("enabled", True)
            
            if not name or not url:
                self.send_json_response({"error": "Name and URL are required"}, 400)
                return
            
            try:
                endpoint = add_endpoint(name, url, enabled)
                self.send_json_response(endpoint, 201)
            except Exception as e:
                self.send_json_response({"error": str(e)}, 400)
        
        elif path == "/api/restore":
            if not self.require_auth():
                return
            try:
                body = self.read_body()
                endpoints_data = body.get("endpoints", [])
                
                if not endpoints_data:
                    self.send_json_response({"error": "No endpoints data provided"}, 400)
                    return
                
                # Clear existing endpoints and restore from backup
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM mcp_endpoints")
                    
                    for ep in endpoints_data:
                        cursor.execute(
                            """
                            INSERT INTO mcp_endpoints (name, url, enabled, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                ep.get("name", "Unnamed"),
                                ep.get("url", ""),
                                1 if ep.get("enabled", True) else 0,
                                ep.get("created_at", datetime.now(timezone.utc).isoformat()),
                                datetime.now(timezone.utc).isoformat()
                            )
                        )
                    
                    conn.commit()
                    logger.info(f"Restored {len(endpoints_data)} endpoints from backup")
                    self.send_json_response({"success": True, "restored": len(endpoints_data)})
                finally:
                    conn.close()
            except Exception as e:
                logger.error(f"Restore failed: {e}")
                self.send_json_response({"error": str(e)}, 400)
        
        elif path == "/api/mcp-servers":
            if not self.require_auth():
                return
            try:
                body = self.read_body()
                name = body.get("name", "").strip()
                
                if not name:
                    self.send_json_response({"error": "Server name is required"}, 400)
                    return
                
                config = load_mcp_config()
                if name in config.get("mcpServers", {}):
                    self.send_json_response({"error": "Server with this name already exists"}, 400)
                    return
                
                server_type = body.get("type", "stdio")
                
                if server_type == "http":
                    server_config = {
                        "type": "http",
                        "url": body.get("url", "")
                    }
                    if body.get("headers"):
                        server_config["headers"] = body.get("headers")
                else:
                    server_config = {
                        "type": server_type,
                        "command": body.get("command", ""),
                        "args": body.get("args", [])
                    }
                    if body.get("env"):
                        server_config["env"] = body.get("env")
                
                if body.get("disabled"):
                    server_config["disabled"] = True
                
                if "mcpServers" not in config:
                    config["mcpServers"] = {}
                config["mcpServers"][name] = server_config
                
                if save_mcp_config(config):
                    logger.info(f"Created MCP server: {name}")
                    self.send_json_response({"success": True, "name": name}, 201)
                else:
                    self.send_json_response({"error": "Failed to save config"}, 500)
            except Exception as e:
                logger.error(f"Create MCP server failed: {e}")
                self.send_json_response({"error": str(e)}, 400)
        
        elif path == "/api/mcp-config/restore":
            if not self.require_auth():
                return
            try:
                body = self.read_body()
                mcp_servers = body.get("mcpServers", {})
                
                if not mcp_servers:
                    self.send_json_response({"error": "No mcpServers data provided"}, 400)
                    return
                
                # Replace entire config
                new_config = {"mcpServers": mcp_servers}
                
                if save_mcp_config(new_config):
                    logger.info(f"Restored {len(mcp_servers)} MCP servers from backup")
                    self.send_json_response({"success": True, "restored": len(mcp_servers)})
                else:
                    self.send_json_response({"error": "Failed to save config"}, 500)
            except Exception as e:
                logger.error(f"Restore MCP config failed: {e}")
                self.send_json_response({"error": str(e)}, 400)
        
        elif path == "/api/mcp-tools/toggle":
            if not self.require_auth():
                return
            try:
                body = self.read_body()
                server_name = body.get("serverName", "").strip()
                tool_name = body.get("toolName", "").strip()
                enabled = body.get("enabled", True)
                
                if not server_name or not tool_name:
                    self.send_json_response({"error": "serverName and toolName are required"}, 400)
                    return
                
                tools_config = load_tools_config()
                disabled_tools = tools_config.get("disabledTools", {})
                
                if not enabled:
                    # Disable the tool
                    if server_name not in disabled_tools:
                        disabled_tools[server_name] = []
                    if tool_name not in disabled_tools[server_name]:
                        disabled_tools[server_name].append(tool_name)
                        logger.info(f"Disabled tool '{tool_name}' from server '{server_name}'")
                else:
                    # Enable the tool
                    if server_name in disabled_tools and tool_name in disabled_tools[server_name]:
                        disabled_tools[server_name].remove(tool_name)
                        logger.info(f"Enabled tool '{tool_name}' from server '{server_name}'")
                        # Clean up empty server entries
                        if not disabled_tools[server_name]:
                            del disabled_tools[server_name]
                
                tools_config["disabledTools"] = disabled_tools
                
                if save_tools_config(tools_config):
                    self.send_json_response({"success": True, "enabled": enabled})
                else:
                    self.send_json_response({"error": "Failed to save config"}, 500)
            except Exception as e:
                logger.error(f"Toggle tool failed: {e}")
                self.send_json_response({"error": str(e)}, 400)
        
        elif path == "/api/mcp-tools/update":
            if not self.require_auth():
                return
            try:
                body = self.read_body()
                server_name = body.get("serverName", "").strip()
                tool_name = body.get("toolName", "").strip()
                custom_name = body.get("customName", "").strip()
                custom_description = body.get("customDescription", "").strip()
                
                if not server_name or not tool_name:
                    self.send_json_response({"error": "serverName and toolName are required"}, 400)
                    return
                
                tools_config = load_tools_config()
                custom_tools = tools_config.get("customTools", {})
                
                # Initialize server entry if needed
                if server_name not in custom_tools:
                    custom_tools[server_name] = {}
                
                # Store custom metadata
                tool_meta = {}
                if custom_name:
                    tool_meta["name"] = custom_name
                if custom_description:
                    tool_meta["description"] = custom_description
                
                if tool_meta:
                    custom_tools[server_name][tool_name] = tool_meta
                    logger.info(f"Updated tool '{tool_name}' from server '{server_name}': {tool_meta}")
                
                tools_config["customTools"] = custom_tools
                
                if save_tools_config(tools_config):
                    self.send_json_response({"success": True, "customMeta": tool_meta})
                else:
                    self.send_json_response({"error": "Failed to save config"}, 500)
            except Exception as e:
                logger.error(f"Update tool failed: {e}")
                self.send_json_response({"error": str(e)}, 400)
        
        elif path == "/api/mcp-tools/reset":
            if not self.require_auth():
                return
            try:
                body = self.read_body()
                server_name = body.get("serverName", "").strip()
                tool_name = body.get("toolName", "").strip()
                
                if not server_name or not tool_name:
                    self.send_json_response({"error": "serverName and toolName are required"}, 400)
                    return
                
                tools_config = load_tools_config()
                custom_tools = tools_config.get("customTools", {})
                
                # Remove custom metadata
                if server_name in custom_tools and tool_name in custom_tools[server_name]:
                    del custom_tools[server_name][tool_name]
                    logger.info(f"Reset tool '{tool_name}' from server '{server_name}'")
                    
                    # Clean up empty server entries
                    if not custom_tools[server_name]:
                        del custom_tools[server_name]
                
                tools_config["customTools"] = custom_tools
                
                if save_tools_config(tools_config):
                    self.send_json_response({"success": True})
                else:
                    self.send_json_response({"error": "Failed to save config"}, 500)
            except Exception as e:
                logger.error(f"Reset tool failed: {e}")
                self.send_json_response({"error": str(e)}, 400)
        
        else:
            self.send_json_response({"error": "Not found"}, 404)
    
    def do_PUT(self):
        """Handle PUT requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path.startswith("/api/endpoints/"):
            if not self.require_auth():
                return
            try:
                endpoint_id = int(path.split("/")[-1])
                body = self.read_body()
                
                endpoint = update_endpoint(
                    endpoint_id,
                    name=body.get("name"),
                    url=body.get("url"),
                    enabled=body.get("enabled")
                )
                
                if endpoint:
                    self.send_json_response(endpoint)
                else:
                    self.send_json_response({"error": "Not found"}, 404)
            except ValueError:
                self.send_json_response({"error": "Invalid ID"}, 400)
        
        elif path.startswith("/api/mcp-servers/"):
            if not self.require_auth():
                return
            try:
                # URL decode the server name
                server_name = unquote(path.split("/api/mcp-servers/")[1])
                body = self.read_body()
                
                config = load_mcp_config()
                if server_name not in config.get("mcpServers", {}):
                    self.send_json_response({"error": "Server not found"}, 404)
                    return
                
                server = config["mcpServers"][server_name]
                
                # Update type and clean up type-specific fields
                if "type" in body:
                    new_type = body["type"]
                    server["type"] = new_type
                    
                    # Clean up fields that don't belong to this type
                    if new_type == "http":
                        # Remove stdio-specific fields
                        for key in ["command", "args", "env"]:
                            if key in server:
                                del server[key]
                    else:
                        # Remove http-specific fields
                        for key in ["url", "headers"]:
                            if key in server:
                                del server[key]
                
                # Update type-specific fields
                server_type = server.get("type", "stdio")
                
                if server_type == "http":
                    # HTTP type fields
                    if "url" in body:
                        server["url"] = body["url"]
                    if "headers" in body:
                        if body["headers"]:
                            server["headers"] = body["headers"]
                        elif "headers" in server:
                            del server["headers"]
                else:
                    # stdio type fields
                    if "command" in body:
                        server["command"] = body["command"]
                    if "args" in body:
                        server["args"] = body["args"]
                    if "env" in body:
                        if body["env"]:
                            server["env"] = body["env"]
                        elif "env" in server:
                            del server["env"]
                
                if "disabled" in body:
                    if body["disabled"]:
                        server["disabled"] = True
                    elif "disabled" in server:
                        del server["disabled"]
                
                if save_mcp_config(config):
                    logger.info(f"Updated MCP server: {server_name}")
                    self.send_json_response({"success": True, "name": server_name})
                else:
                    self.send_json_response({"error": "Failed to save config"}, 500)
            except Exception as e:
                logger.error(f"Update MCP server failed: {e}")
                self.send_json_response({"error": str(e)}, 400)
        
        else:
            self.send_json_response({"error": "Not found"}, 404)
    
    def do_DELETE(self):
        """Handle DELETE requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path.startswith("/api/endpoints/"):
            if not self.require_auth():
                return
            try:
                endpoint_id = int(path.split("/")[-1])
                if delete_endpoint(endpoint_id):
                    self.send_json_response({"success": True})
                else:
                    self.send_json_response({"error": "Not found"}, 404)
            except ValueError:
                self.send_json_response({"error": "Invalid ID"}, 400)
        
        elif path.startswith("/api/mcp-servers/"):
            if not self.require_auth():
                return
            try:
                server_name = unquote(path.split("/api/mcp-servers/")[1])
                
                config = load_mcp_config()
                if server_name not in config.get("mcpServers", {}):
                    self.send_json_response({"error": "Server not found"}, 404)
                    return
                
                del config["mcpServers"][server_name]
                
                if save_mcp_config(config):
                    logger.info(f"Deleted MCP server: {server_name}")
                    self.send_json_response({"success": True})
                else:
                    self.send_json_response({"error": "Failed to save config"}, 500)
            except Exception as e:
                logger.error(f"Delete MCP server failed: {e}")
                self.send_json_response({"error": str(e)}, 400)
        
        else:
            self.send_json_response({"error": "Not found"}, 404)


def main():
    """Run the CMS server."""
    # Initialize database
    init_db()
    
    # Start server
    server = HTTPServer(("0.0.0.0", HTTP_PORT), CMSHandler)
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    MCP Endpoints CMS Server                      ║
╠══════════════════════════════════════════════════════════════════╣
║  Admin Interface: http://localhost:{HTTP_PORT:<5}                        ║
║                                                                  ║
║  Default credentials:                                            ║
║    Username: {CMS_USERNAME:<20}                             ║
║    Password: {'*' * min(len(CMS_PASSWORD), 10):<20}                             ║
║                                                                  ║
║  Set CMS_USERNAME, CMS_PASSWORD in .env to change               ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCMS server stopped.")


if __name__ == "__main__":
    main()
