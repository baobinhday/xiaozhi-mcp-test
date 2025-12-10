"""MCP Server for Search and News tools."""
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
# from tools.search_tools import tim_kiem_web
from tools.new_tools import get_latest_news

# Create MCP server
mcp = FastMCP("SearchAndNews")

# Register tools
# mcp.tool()(tim_kiem_web)
mcp.tool()(get_latest_news)

# Start the server
if __name__ == "__main__":
    print("[MCP Server] Starting SearchAndNews server...")
    mcp.run(transport="stdio")
