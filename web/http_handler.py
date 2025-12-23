"""
HTTP Server and AuthHandler for MCP Web Tester.
"""

import json
import logging
import socketserver
import sys
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from auth import (
    WEB_USERNAME, WEB_PASSWORD, SESSION_DURATION_HOURS,
    create_session, validate_session, destroy_session,
    get_client_ip, check_rate_limit, record_login_attempt
)
from edge_tts_api import handle_voices_request, handle_synthesize_request

logger = logging.getLogger('MCP_HUB')


class AuthHandler(SimpleHTTPRequestHandler):
    """HTTP handler with session-based authentication."""
    
    web_dir = None  # Set by run_http_server
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.web_dir), **kwargs)
    
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
        
        # Edge TTS voices API (no auth required for TTS)
        if path == "/api/edge-tts/voices":
            handle_voices_request(self)
            return
        
        # Protected static files - redirect to login if not authenticated
        # Allow CSS, JS, and fonts without auth for login page styling
        allowed_without_auth = [
            '/style.css', '/common.css', '/app.js', 
            '/js/', '/libs/', '/login.html'
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
            
            if username == WEB_USERNAME and password == WEB_PASSWORD:
                record_login_attempt(client_ip, True, logger)
                token = create_session(username)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie", f"web_session={token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age={SESSION_DURATION_HOURS * 3600}")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "message": "Login successful"}).encode())
            else:
                record_login_attempt(client_ip, False, logger)
                self.send_json_response({"error": "Invalid credentials"}, 401)
        
        elif path == "/api/logout":
            token = self.get_session_token()
            destroy_session(token)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", "web_session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode())
        
        elif path == "/api/edge-tts/synthesize":
            body = self.read_body()
            handle_synthesize_request(self, body)
        
        else:
            self.send_json_response({"error": "Not found"}, 404)


class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


def run_http_server(http_port: int, web_dir: Path):
    """Run HTTP server for static files with authentication (blocking)."""
    AuthHandler.web_dir = web_dir
    server = ThreadedServer(("0.0.0.0", http_port), AuthHandler)
    logger.info(f"HTTP server running on http://localhost:{http_port}")
    server.serve_forever()
