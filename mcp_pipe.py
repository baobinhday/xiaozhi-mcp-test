#!/usr/bin/env python3
"""
MCP WebSocket-stdio pipe entry point.

This is a thin wrapper that delegates to the mcp_xiaozhi package.
For the full implementation, see src/mcp_xiaozhi/main.py.

Usage:
    python mcp_pipe.py                    # Run all configured servers
    python mcp_pipe.py path/to/server.py  # Run a single server script

Environment variables:
    MCP_ENDPOINT: WebSocket endpoint URL (required)
    MCP_CONFIG: Path to config file (optional, defaults to ./mcp_config.json)
"""

import sys
import os

# Add src to path for development (before package is installed)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mcp_xiaozhi.main import main

if __name__ == "__main__":
    main()