"""MCP Server for Fortune Telling (Xem Bói) tools."""

import os
import sys

# Add project root to path for standalone execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from tools.fortune_tools import (
    xem_cung_hoang_dao,
    xem_con_giap,
    xem_menh_ngu_hanh,
    xem_tuoi_hop_nhau,
    boi_que_kinh_dich,
    xem_so_may_man,
    du_bao_ngay_hom_nay,
    xem_ngay_tot_xau,
)

# Create MCP server
mcp = FastMCP("Fortune")

# Register all fortune telling tools
mcp.tool()(xem_cung_hoang_dao)
mcp.tool()(xem_con_giap)
mcp.tool()(xem_menh_ngu_hanh)
mcp.tool()(xem_tuoi_hop_nhau)
mcp.tool()(boi_que_kinh_dich)
mcp.tool()(xem_so_may_man)
mcp.tool()(du_bao_ngay_hom_nay)
mcp.tool()(xem_ngay_tot_xau)

# Start the server
if __name__ == "__main__":
    print("[MCP Server] Starting Fortune Telling server...")
    mcp.run(transport="stdio")
