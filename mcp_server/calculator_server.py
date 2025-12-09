"""MCP Server for Calculator tool."""
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from tools.math_tools import calculator

# Create MCP server
mcp = FastMCP("Calculator")

# Register tools
mcp.tool()(calculator)

# Start the server
if __name__ == "__main__":
    print("[MCP Server] Starting Calculator server...")
    mcp.run(transport="stdio")
