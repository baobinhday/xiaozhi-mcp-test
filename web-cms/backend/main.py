#!/usr/bin/env python3
"""
MCP Endpoints CMS - Web admin interface for managing MCP endpoints.

Usage:
    python3 -m backend.main [port]
    
    Default: HTTP on 8890

Built with FastAPI for proper SSE support.
"""

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))  # web-cms
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # project root

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import CMS_DIR, CMS_PASSWORD, CMS_USERNAME, HTTP_PORT
from backend.routes import auth, endpoints, mcp_servers, mcp_tools

# Import database init from src
from src.mcp_xiaozhi.database import init_db


# =========================== FastAPI App ===========================

app = FastAPI(title="MCP Endpoints CMS", docs_url=None, redoc_url=None)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(endpoints.router)
app.include_router(mcp_servers.router)
app.include_router(mcp_tools.router)


# =========================== Static Files ===========================

@app.get("/")
async def serve_index():
    """Serve index.html at root."""
    return FileResponse(CMS_DIR / "index.html")


# Mount static files for JS and CSS
app.mount("/js", StaticFiles(directory=CMS_DIR / "js"), name="js")
app.mount("/", StaticFiles(directory=CMS_DIR), name="static")


# =========================== Main ===========================

def main():
    """Run the CMS server."""
    init_db()
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    MCP Endpoints CMS Server                      ║
║                      (Powered by FastAPI)                        ║
╠══════════════════════════════════════════════════════════════════╣
║  Admin Interface: http://localhost:{HTTP_PORT:<5}                ║
║                                                                  ║
║  Default credentials:                                            ║
║    Username: {CMS_USERNAME:<20}                                  ║
║    Password: {'*' * min(len(CMS_PASSWORD), 10):<20}              ║
║                                                                  ║
║  Set CMS_USERNAME, CMS_PASSWORD in .env to change                ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT, log_level="info")


if __name__ == "__main__":
    main()
