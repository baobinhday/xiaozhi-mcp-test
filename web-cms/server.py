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
import subprocess
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
    get_all_tool_settings_for_backup,
    get_connection,
    get_custom_tools,
    get_disabled_tools,
    get_endpoint_by_id,
    init_db,
    reset_tool_metadata,
    restore_tool_settings,
    set_tool_custom_metadata,
    set_tool_enabled,
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

# Rate limiting storage
login_attempts = {}  # Dict: ip -> {"count": int, "first_attempt": datetime, "last_failed": datetime}
MAX_LOGIN_ATTEMPTS = 3
RATE_LIMIT_WINDOW = 60  # seconds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('CMS')

# MCP Config file path
MCP_CONFIG_PATH = Path(__file__).parent.parent / "data" / "mcp_config.json"

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


def discover_tools_for_server(server_name: str, server_config: dict) -> list:
    """Start MCP server process temporarily, query tools via stdio, and cache them.
    
    This allows the CMS to discover tools immediately when a server is added,
    without requiring an endpoint connection.
    
    Args:
        server_name: Name of the MCP server
        server_config: Server configuration dict from mcp_config.json
        
    Returns:
        List of tools discovered, or empty list on failure
    """
    # Skip if disabled
    if server_config.get("disabled"):
        logger.info(f"[{server_name}] Skipping tool discovery - server is disabled")
        return []
    
    server_type = server_config.get("type", "stdio")
    
    # Build command based on server type
    try:
        if server_type == "stdio":
            command = server_config.get("command")
            args = server_config.get("args", [])
            if not command:
                logger.error(f"[{server_name}] Missing 'command' in config")
                return []
            cmd = [command] + args
        elif server_type in ("http", "sse", "streamablehttp"):
            url = server_config.get("url")
            if not url:
                logger.error(f"[{server_name}] Missing 'url' for HTTP type server")
                return []
            # Use mcp-proxy for HTTP servers
            cmd = [sys.executable, "-m", "mcp_proxy"]
            if server_type in ("http", "streamablehttp"):
                cmd += ["--transport", "streamablehttp"]
            headers = server_config.get("headers", {})
            for hk, hv in headers.items():
                cmd += ["-H", hk, str(hv)]
            cmd.append(url)
        else:
            logger.error(f"[{server_name}] Unsupported server type: {server_type}")
            return []
    except Exception as e:
        logger.error(f"[{server_name}] Error building command: {e}")
        return []
    
    # Build environment
    child_env = os.environ.copy()
    for k, v in server_config.get("env", {}).items():
        child_env[str(k)] = str(v)
    
    process = None
    tools = []
    
    try:
        logger.info(f"[{server_name}] Starting process for tool discovery: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            env=child_env,
        )
        
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": "cms_init",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "MCP CMS Tool Discovery",
                    "version": "1.0.0"
                }
            }
        }
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read initialize response (with timeout via select/poll would be ideal, but simple readline for now)
        init_response_line = process.stdout.readline()
        if not init_response_line:
            logger.error(f"[{server_name}] No response to initialize request")
            return []
        
        try:
            init_response = json.loads(init_response_line)
            if "error" in init_response:
                logger.error(f"[{server_name}] Initialize error: {init_response['error']}")
                return []
            logger.info(f"[{server_name}] Initialize successful")
        except json.JSONDecodeError:
            logger.error(f"[{server_name}] Invalid JSON in initialize response")
            return []
        
        # Send tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": "cms_tools_list",
            "method": "tools/list",
            "params": {}
        }
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        # Read tools/list response
        tools_response_line = process.stdout.readline()
        if not tools_response_line:
            logger.error(f"[{server_name}] No response to tools/list request")
            return []
        
        try:
            tools_response = json.loads(tools_response_line)
            if "error" in tools_response:
                logger.error(f"[{server_name}] tools/list error: {tools_response['error']}")
                return []
            
            tools = tools_response.get("result", {}).get("tools", [])
            logger.info(f"[{server_name}] Discovered {len(tools)} tools")
        except json.JSONDecodeError:
            logger.error(f"[{server_name}] Invalid JSON in tools/list response")
            return []
        
        # Cache tools to tools_cache.json
        if tools:
            try:
                cache = {}
                if TOOLS_CACHE_PATH.exists():
                    with open(TOOLS_CACHE_PATH, 'r') as f:
                        cache = json.load(f)
                
                cache[server_name] = tools
                
                with open(TOOLS_CACHE_PATH, 'w') as f:
                    json.dump(cache, f, indent=2, ensure_ascii=False)
                
                logger.info(f"[{server_name}] Cached {len(tools)} tools for CMS")
            except Exception as e:
                logger.error(f"[{server_name}] Failed to cache tools: {e}")
        
        return tools
        
    except Exception as e:
        logger.error(f"[{server_name}] Tool discovery failed: {e}")
        return []
    
    finally:
        # Ensure process is terminated
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception:
                pass
            logger.info(f"[{server_name}] Process terminated")


def remove_tools_from_cache(server_name: str) -> None:
    """Remove tools from cache when MCP server is disabled or deleted."""
    try:
        if not TOOLS_CACHE_PATH.exists():
            return
        
        with open(TOOLS_CACHE_PATH, 'r') as f:
            cache = json.load(f)
        
        if server_name in cache:
            del cache[server_name]
            
            with open(TOOLS_CACHE_PATH, 'w') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[{server_name}] Removed tools from cache")
    except Exception as e:
        logger.error(f"Failed to remove tools from cache: {e}")


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


def get_client_ip(handler) -> str:
    """Get client IP from request."""
    # Check for forwarded header first (behind proxy)
    forwarded = handler.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return handler.client_address[0]


def check_rate_limit(ip: str) -> tuple:
    """Check if IP is rate limited. Returns (allowed, wait_seconds)."""
    if ip not in login_attempts:
        return True, 0
    
    attempt = login_attempts[ip]
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    
    # Reset if outside window
    if attempt["first_attempt"] < window_start:
        del login_attempts[ip]
        return True, 0
    
    # Check attempt count
    if attempt["count"] >= MAX_LOGIN_ATTEMPTS:
        # Exponential backoff: 2^(attempts - MAX) seconds, max 5 minutes
        backoff = min(2 ** (attempt["count"] - MAX_LOGIN_ATTEMPTS + 1), 300)
        wait_until = attempt["last_failed"] + timedelta(seconds=backoff)
        if now < wait_until:
            return False, int((wait_until - now).total_seconds()) + 1
    
    return True, 0


def record_login_attempt(ip: str, success: bool):
    """Record a login attempt."""
    now = datetime.now(timezone.utc)
    if success:
        # Clear on successful login
        login_attempts.pop(ip, None)
    else:
        if ip not in login_attempts:
            login_attempts[ip] = {"count": 0, "first_attempt": now, "last_failed": now}
        login_attempts[ip]["count"] += 1
        login_attempts[ip]["last_failed"] = now
        logger.warning(f"Failed login attempt from {ip} (count: {login_attempts[ip]['count']})")


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
            # Get tools config for disabled tools and custom metadata from database
            self.send_json_response({
                "disabledTools": get_disabled_tools(),
                "customTools": get_custom_tools()
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
        
        elif path == "/api/mcp-tools/backup":
            if not self.require_auth():
                return
            tool_settings = get_all_tool_settings_for_backup()
            backup_data = {
                "version": "1.0",
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "disabledTools": tool_settings.get("disabledTools", {}),
                "customTools": tool_settings.get("customTools", {})
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition", "attachment; filename=tools_config_backup.json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(backup_data, indent=2).encode())
        
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
            # Rate limiting check
            client_ip = get_client_ip(self)
            allowed, wait_seconds = check_rate_limit(client_ip)
            if not allowed:
                logger.warning(f"Rate limited login attempt from {client_ip}")
                self.send_json_response({
                    "error": f"Too many login attempts. Please wait {wait_seconds} seconds."
                }, 429)
                return
            
            body = self.read_body()
            username = body.get("username", "")
            password = body.get("password", "")
            
            if username == CMS_USERNAME and password == CMS_PASSWORD:
                record_login_attempt(client_ip, True)
                token = create_session(username)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie", f"session={token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age={SESSION_DURATION_HOURS * 3600}")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "message": "Login successful"}).encode())
            else:
                record_login_attempt(client_ip, False)
                self.send_json_response({"error": "Invalid credentials"}, 401)
        
        elif path == "/api/logout":
            token = self.get_session_token()
            destroy_session(token)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", "session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0")
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
                    # Discover tools immediately (in background)
                    if not server_config.get("disabled"):
                        tools = discover_tools_for_server(name, server_config)
                        self.send_json_response({"success": True, "name": name, "tools_discovered": len(tools)}, 201)
                    else:
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
                
                if set_tool_enabled(server_name, tool_name, enabled):
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
                custom_name = body.get("customName", "").strip() or None
                custom_description = body.get("customDescription", "").strip() or None
                
                if not server_name or not tool_name:
                    self.send_json_response({"error": "serverName and toolName are required"}, 400)
                    return
                
                if set_tool_custom_metadata(server_name, tool_name, custom_name, custom_description):
                    tool_meta = {}
                    if custom_name:
                        tool_meta["name"] = custom_name
                    if custom_description:
                        tool_meta["description"] = custom_description
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
                
                if reset_tool_metadata(server_name, tool_name):
                    self.send_json_response({"success": True})
                else:
                    self.send_json_response({"error": "Failed to save config"}, 500)
            except Exception as e:
                logger.error(f"Reset tool failed: {e}")
                self.send_json_response({"error": str(e)}, 400)
        
        elif path == "/api/mcp-tools/restore":
            if not self.require_auth():
                return
            try:
                body = self.read_body()
                disabled_tools = body.get("disabledTools", {})
                custom_tools = body.get("customTools", {})
                
                if not isinstance(disabled_tools, dict):
                    self.send_json_response({"error": "Invalid disabledTools format"}, 400)
                    return
                
                if restore_tool_settings(disabled_tools, custom_tools):
                    self.send_json_response({"success": True})
                else:
                    self.send_json_response({"error": "Failed to save config"}, 500)
            except Exception as e:
                logger.error(f"Restore tools config failed: {e}")
                self.send_json_response({"error": str(e)}, 400)
        
        elif path == "/api/mcp-tools/refresh":
            if not self.require_auth():
                return
            try:
                body = self.read_body()
                server_name = body.get("serverName", "").strip()
                
                config = load_mcp_config()
                
                if server_name:
                    # Refresh specific server
                    if server_name not in config.get("mcpServers", {}):
                        self.send_json_response({"error": "Server not found"}, 404)
                        return
                    
                    server_config = config["mcpServers"][server_name]
                    tools = discover_tools_for_server(server_name, server_config)
                    self.send_json_response({"success": True, "server": server_name, "tools_discovered": len(tools)})
                else:
                    # Refresh all enabled servers
                    total_tools = 0
                    servers_refreshed = []
                    
                    for name, server_config in config.get("mcpServers", {}).items():
                        if not server_config.get("disabled"):
                            tools = discover_tools_for_server(name, server_config)
                            total_tools += len(tools)
                            servers_refreshed.append(name)
                    
                    self.send_json_response({
                        "success": True,
                        "servers_refreshed": servers_refreshed,
                        "total_tools_discovered": total_tools
                    })
            except Exception as e:
                logger.error(f"Refresh tools failed: {e}")
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
                was_disabled = server.get("disabled", False)
                
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
                
                is_now_disabled = server.get("disabled", False)
                
                if save_mcp_config(config):
                    logger.info(f"Updated MCP server: {server_name}")
                    
                    # Handle tool discovery based on disabled state change
                    if was_disabled and not is_now_disabled:
                        # Server was enabled - discover tools
                        tools = discover_tools_for_server(server_name, server)
                        self.send_json_response({"success": True, "name": server_name, "tools_discovered": len(tools)})
                    elif not was_disabled and is_now_disabled:
                        # Server was disabled - remove tools from cache
                        remove_tools_from_cache(server_name)
                        self.send_json_response({"success": True, "name": server_name})
                    else:
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
                    # Remove tools from cache
                    remove_tools_from_cache(server_name)
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
