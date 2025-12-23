#!/usr/bin/env python3
"""
MCP Endpoints CMS - Web admin interface for managing MCP endpoints.

Usage:
    python3 server.py [port]
    
    Default: HTTP on 8890

Built with FastAPI for proper SSE support.

This is a compatibility wrapper that imports from the refactored backend package.
"""

import sys
from pathlib import Path

# Add current directory to path for backend package imports
sys.path.insert(0, str(Path(__file__).parent))

from backend.main import main

if __name__ == "__main__":
    main()
