"""MCP Server for News tool."""

import os
import sys

# Add project root to path for standalone execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from tools.news_tools import (
    get_latest_news_from_vnexpress,
    get_detail_news_content_from_vnexpress,
    get_latest_news_from_dantri,
    get_detail_news_content_from_dantri
)
from tools.gold_tools import (
    get_all_gold_prices,
    get_doji_gold_price,
    get_pnj_gold_price,
    get_sjc_gold_price,
)

# Create MCP server
mcp = FastMCP("News")

# Register tools
mcp.tool()(get_latest_news_from_vnexpress)
mcp.tool()(get_detail_news_content_from_vnexpress)
mcp.tool()(get_latest_news_from_dantri)
mcp.tool()(get_detail_news_content_from_dantri)
mcp.tool()(get_all_gold_prices)
mcp.tool()(get_doji_gold_price)
mcp.tool()(get_pnj_gold_price)
mcp.tool()(get_sjc_gold_price)

# Start the server
if __name__ == "__main__":
    print("[MCP Server] Starting News server...")
    mcp.run(transport="stdio")
