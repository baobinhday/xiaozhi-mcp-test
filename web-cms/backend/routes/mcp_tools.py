"""
MCP Tools routes.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.config import TOOLS_CACHE_PATH, logger
from backend.dependencies import require_auth
from backend.schemas.mcp_tools import ToolRefresh, ToolReset, ToolToggle, ToolUpdate
from backend.services.mcp_config import load_mcp_config
from backend.services.tool_discovery import discover_tools_for_server

# Import database functions - add parent to path if needed
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.mcp_xiaozhi.database import (
    get_all_tool_settings_for_backup,
    get_custom_tools,
    get_disabled_tools,
    reset_tool_metadata,
    restore_tool_settings,
    set_tool_custom_metadata,
    set_tool_enabled,
)

router = APIRouter(prefix="/api", tags=["mcp-tools"])


@router.get("/mcp-tools")
async def get_mcp_tools(_: str = Depends(require_auth)):
    return {
        "disabledTools": get_disabled_tools(),
        "customTools": get_custom_tools()
    }


@router.get("/mcp-tools/cache")
async def get_tools_cache(_: str = Depends(require_auth)):
    try:
        if TOOLS_CACHE_PATH.exists():
            with open(TOOLS_CACHE_PATH, 'r') as f:
                tools_cache = json.load(f)
            return {"tools": tools_cache}
        return {"tools": {}}
    except Exception as e:
        logger.error(f"Error reading tools cache: {e}")
        return {"tools": {}}


@router.post("/mcp-tools/toggle")
async def toggle_tool(body: ToolToggle, _: str = Depends(require_auth)):
    if not body.serverName or not body.toolName:
        raise HTTPException(status_code=400, detail="serverName and toolName are required")
    
    if set_tool_enabled(body.serverName, body.toolName, body.enabled):
        return {"success": True, "enabled": body.enabled}
    
    raise HTTPException(status_code=500, detail="Failed to save config")


@router.post("/mcp-tools/update")
async def update_tool(body: ToolUpdate, _: str = Depends(require_auth)):
    if not body.serverName or not body.toolName:
        raise HTTPException(status_code=400, detail="serverName and toolName are required")
    
    custom_name = body.customName.strip() if body.customName else None
    custom_description = body.customDescription.strip() if body.customDescription else None
    
    if set_tool_custom_metadata(body.serverName, body.toolName, custom_name, custom_description):
        tool_meta = {}
        if custom_name:
            tool_meta["name"] = custom_name
        if custom_description:
            tool_meta["description"] = custom_description
        return {"success": True, "customMeta": tool_meta}
    
    raise HTTPException(status_code=500, detail="Failed to save config")


@router.post("/mcp-tools/reset")
async def reset_tool(body: ToolReset, _: str = Depends(require_auth)):
    if not body.serverName or not body.toolName:
        raise HTTPException(status_code=400, detail="serverName and toolName are required")
    
    if reset_tool_metadata(body.serverName, body.toolName):
        return {"success": True}
    
    raise HTTPException(status_code=500, detail="Failed to save config")


@router.get("/mcp-tools/backup")
async def backup_tools(_: str = Depends(require_auth)):
    tool_settings = get_all_tool_settings_for_backup()
    backup_data = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "disabledTools": tool_settings.get("disabledTools", {}),
        "customTools": tool_settings.get("customTools", {})
    }
    return Response(
        content=json.dumps(backup_data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=tools_config_backup.json"}
    )


@router.post("/mcp-tools/restore")
async def restore_tools(request: Request, _: str = Depends(require_auth)):
    body = await request.json()
    disabled_tools = body.get("disabledTools", {})
    custom_tools = body.get("customTools", {})
    
    if not isinstance(disabled_tools, dict):
        raise HTTPException(status_code=400, detail="Invalid disabledTools format")
    
    if restore_tool_settings(disabled_tools, custom_tools):
        return {"success": True}
    
    raise HTTPException(status_code=500, detail="Failed to save config")


@router.post("/mcp-tools/refresh")
async def refresh_tools(body: ToolRefresh, _: str = Depends(require_auth)):
    config = load_mcp_config()
    
    if body.serverName:
        if body.serverName not in config.get("mcpServers", {}):
            raise HTTPException(status_code=404, detail="Server not found")
        
        server_config = config["mcpServers"][body.serverName]
        tools = discover_tools_for_server(body.serverName, server_config)
        return {"success": True, "server": body.serverName, "tools_discovered": len(tools)}
    else:
        total_tools = 0
        servers_refreshed = []
        
        for name, server_config in config.get("mcpServers", {}).items():
            if not server_config.get("disabled"):
                tools = discover_tools_for_server(name, server_config)
                total_tools += len(tools)
                servers_refreshed.append(name)
        
        return {
            "success": True,
            "servers_refreshed": servers_refreshed,
            "total_tools_discovered": total_tools
        }
