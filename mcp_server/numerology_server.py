"""MCP Server for Numerology (Thần Số Học) tools."""

import os
import sys

# Add project root to path for standalone execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from tools.numerology_tools import (
    life_path,
    destiny,
    soul_urge,
    personality,
    personal_year,
    full_profile,
)

# Create MCP server
mcp = FastMCP("Numerology")

# Register all numerology tools
mcp.tool()(life_path)
mcp.tool()(destiny)
mcp.tool()(soul_urge)
mcp.tool()(personality)
mcp.tool()(personal_year)
mcp.tool()(full_profile)

# Start the server
if __name__ == "__main__":
    print("[MCP Server] Starting Numerology server...")
    mcp.run(transport="stdio")
