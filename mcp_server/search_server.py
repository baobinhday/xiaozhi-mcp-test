"""MCP Server for News tool."""

import os
import sys

# Add project root to path for standalone execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from tools.news_tools import get_latest_news

# Create MCP server
mcp = FastMCP("SearchAndNews")

# Register tools
mcp.tool()(get_latest_news)

# Start the server
if __name__ == "__main__":
    print("[MCP Server] Starting SearchAndNews server...")
    mcp.run(transport="stdio")
