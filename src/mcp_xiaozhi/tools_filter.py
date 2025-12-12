"""Tools configuration and filtering for MCP Xiaozhi."""

import json
import logging
import os
from typing import Any

logger = logging.getLogger("MCP_PIPE")

# Path to tools cache file (all tools from MCP servers, for CMS)
TOOLS_CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "tools_cache.json")

# Import database functions for tool settings
from src.mcp_xiaozhi.database import get_disabled_tools, get_custom_tools


def cache_tools_for_cms(server_name: str, tools: list) -> None:
    """Cache tools from MCP server for CMS to read.
    
    Writes ALL tools (unfiltered) to a cache file so CMS can display
    and manage them without connecting to the WebSocket hub.
    
    Args:
        server_name: Name of the MCP server
        tools: List of tools from the server
    """
    try:
        # Load existing cache
        cache = {}
        if os.path.exists(TOOLS_CACHE_PATH):
            with open(TOOLS_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
        
        # Update cache with tools from this server
        cache[server_name] = tools
        
        # Write back to file
        with open(TOOLS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[{server_name}] Cached {len(tools)} tools for CMS")
    except Exception as e:
        logger.error(f"Failed to cache tools for CMS: {e}")


def remove_tools_from_cache(server_name: str) -> None:
    """Remove tools from cache when MCP server is disabled.
    
    Args:
        server_name: Name of the MCP server to remove from cache
    """
    try:
        if not os.path.exists(TOOLS_CACHE_PATH):
            return
        
        with open(TOOLS_CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
        
        if server_name in cache:
            del cache[server_name]
            
            with open(TOOLS_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[{server_name}] Removed tools from cache")
    except Exception as e:
        logger.error(f"Failed to remove tools from cache: {e}")


def load_tools_config() -> dict:
    """Load tools configuration from database.
    
    Returns:
        Dictionary with disabledTools and customTools
    """
    try:
        return {
            "disabledTools": get_disabled_tools(),
            "customTools": get_custom_tools()
        }
    except Exception as e:
        logger.debug(f"Failed to load tools config from DB: {e}")
        return {"disabledTools": {}, "customTools": {}}


def filter_tools_response(message: str, server_name: str, include_disabled: bool = False) -> str:
    """Filter tools list response, removing disabled tools and applying custom metadata.
    
    Args:
        message: JSON-RPC message string from MCP server
        server_name: Name of the MCP server
        include_disabled: If True, include all tools (for CMS management)
    
    Returns:
        Modified message string with filtered/customized tools
    """
    try:
        msg = json.loads(message)
        
        # Check if this is a tools/list response
        if "result" not in msg or "tools" not in msg.get("result", {}):
            return message
        
        tools = msg["result"]["tools"]
        config = load_tools_config()
        disabled_tools = config.get("disabledTools", {}).get(server_name, [])
        custom_tools = config.get("customTools", {}).get(server_name, {})
        
        filtered_tools = []
        for tool in tools:
            tool_name = tool.get("name")
            if not tool_name:
                continue
            
            # Skip disabled tools unless include_disabled is True
            if not include_disabled and tool_name in disabled_tools:
                logger.debug(f"[{server_name}] Filtering out disabled tool: {tool_name}")
                continue
            
            # Apply custom metadata if available
            tool_custom = custom_tools.get(tool_name, {})
            if tool_custom:
                tool = tool.copy()  # Don't modify original
                if "description" in tool_custom:
                    tool["description"] = tool_custom["description"]
                # Note: custom name is for display only in CMS, 
                # actual tool name must remain unchanged for calls to work
            
            filtered_tools.append(tool)
        
        # Update the message with filtered tools
        msg["result"]["tools"] = filtered_tools
        logger.info(f"[{server_name}] Filtered tools: {len(tools)} -> {len(filtered_tools)} (include_disabled={include_disabled})")
        
        return json.dumps(msg)
    
    except json.JSONDecodeError:
        # Not valid JSON, return as-is
        return message
    except Exception as e:
        logger.error(f"Error filtering tools response: {e}")
        return message
