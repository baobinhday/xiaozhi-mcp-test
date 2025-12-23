"""
MCP Servers CRUD routes.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.config import logger
from backend.dependencies import require_auth
from backend.schemas.mcp_servers import MCPServerCreate, MCPServerUpdate
from backend.services.mcp_config import load_mcp_config, remove_tools_from_cache, save_mcp_config
from backend.services.tool_discovery import discover_tools_for_server

router = APIRouter(prefix="/api", tags=["mcp-servers"])


@router.get("/mcp-servers")
async def list_mcp_servers(_: str = Depends(require_auth)):
    config = load_mcp_config()
    servers = []
    for name, server in config.get("mcpServers", {}).items():
        servers.append({
            "name": name,
            "type": server.get("type", "stdio"),
            "command": server.get("command", ""),
            "args": server.get("args", []),
            "env": server.get("env", {}),
            "url": server.get("url", ""),
            "headers": server.get("headers", {}),
            "disabled": server.get("disabled", False)
        })
    return {"servers": servers}


@router.post("/mcp-servers", status_code=201)
async def create_mcp_server(body: MCPServerCreate, _: str = Depends(require_auth)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Server name is required")
    
    config = load_mcp_config()
    if body.name in config.get("mcpServers", {}):
        raise HTTPException(status_code=400, detail="Server with this name already exists")
    
    if body.type == "http":
        server_config = {
            "type": "http",
            "url": body.url or ""
        }
        if body.headers:
            server_config["headers"] = body.headers
    else:
        server_config = {
            "type": body.type,
            "command": body.command or "",
            "args": body.args or []
        }
        if body.env:
            server_config["env"] = body.env
    
    if body.disabled:
        server_config["disabled"] = True
    
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    config["mcpServers"][body.name] = server_config
    
    if save_mcp_config(config):
        logger.info(f"Created MCP server: {body.name}")
        if not server_config.get("disabled"):
            tools = discover_tools_for_server(body.name, server_config)
            return {"success": True, "name": body.name, "tools_discovered": len(tools)}
        return {"success": True, "name": body.name}
    
    raise HTTPException(status_code=500, detail="Failed to save config")


@router.put("/mcp-servers/{server_name:path}")
async def update_mcp_server(server_name: str, body: MCPServerUpdate, _: str = Depends(require_auth)):
    config = load_mcp_config()
    if server_name not in config.get("mcpServers", {}):
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = config["mcpServers"][server_name]
    was_disabled = server.get("disabled", False)
    
    # Update type and clean up type-specific fields
    if body.type is not None:
        new_type = body.type
        server["type"] = new_type
        
        if new_type == "http":
            for key in ["command", "args", "env"]:
                if key in server:
                    del server[key]
        else:
            for key in ["url", "headers"]:
                if key in server:
                    del server[key]
    
    server_type = server.get("type", "stdio")
    
    if server_type == "http":
        if body.url is not None:
            server["url"] = body.url
        if body.headers is not None:
            if body.headers:
                server["headers"] = body.headers
            elif "headers" in server:
                del server["headers"]
    else:
        if body.command is not None:
            server["command"] = body.command
        if body.args is not None:
            server["args"] = body.args
        if body.env is not None:
            if body.env:
                server["env"] = body.env
            elif "env" in server:
                del server["env"]
    
    if body.disabled is not None:
        if body.disabled:
            server["disabled"] = True
        elif "disabled" in server:
            del server["disabled"]
    
    is_now_disabled = server.get("disabled", False)
    
    if save_mcp_config(config):
        logger.info(f"Updated MCP server: {server_name}")
        
        if was_disabled and not is_now_disabled:
            tools = discover_tools_for_server(server_name, server)
            return {"success": True, "name": server_name, "tools_discovered": len(tools)}
        elif not was_disabled and is_now_disabled:
            remove_tools_from_cache(server_name)
            return {"success": True, "name": server_name}
        else:
            return {"success": True, "name": server_name}
    
    raise HTTPException(status_code=500, detail="Failed to save config")


@router.delete("/mcp-servers/{server_name:path}")
async def delete_mcp_server(server_name: str, _: str = Depends(require_auth)):
    config = load_mcp_config()
    if server_name not in config.get("mcpServers", {}):
        raise HTTPException(status_code=404, detail="Server not found")
    
    del config["mcpServers"][server_name]
    
    if save_mcp_config(config):
        logger.info(f"Deleted MCP server: {server_name}")
        remove_tools_from_cache(server_name)
        return {"success": True}
    
    raise HTTPException(status_code=500, detail="Failed to save config")


@router.get("/mcp-config/backup")
async def backup_mcp_config(_: str = Depends(require_auth)):
    config = load_mcp_config()
    backup_data = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "mcpServers": config.get("mcpServers", {})
    }
    return Response(
        content=json.dumps(backup_data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=mcp_config_backup.json"}
    )


@router.post("/mcp-config/restore")
async def restore_mcp_config(request: Request, _: str = Depends(require_auth)):
    body = await request.json()
    mcp_servers = body.get("mcpServers", {})
    
    if not mcp_servers:
        raise HTTPException(status_code=400, detail="No mcpServers data provided")
    
    new_config = {"mcpServers": mcp_servers}
    
    if save_mcp_config(new_config):
        logger.info(f"Restored {len(mcp_servers)} MCP servers from backup")
        return {"success": True, "restored": len(mcp_servers)}
    
    raise HTTPException(status_code=500, detail="Failed to save config")
