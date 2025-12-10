"""MCP Server for News tool."""

import os
import sys

# Add project root to path for standalone execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from tools.search_tools import web_search

# Create MCP server
mcp = FastMCP("Search")

# Register tools
mcp.tool()(web_search)

# Start the server
if __name__ == "__main__":
    print("[MCP Server] Starting Search server...")
    mcp.run(transport="stdio")
