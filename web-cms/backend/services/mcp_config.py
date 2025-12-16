"""
MCP Configuration service.

Handles loading, saving mcp_config.json and tools cache management.
"""

import json

from backend.config import MCP_CONFIG_PATH, TOOLS_CACHE_PATH, logger


def load_mcp_config() -> dict:
    """Load MCP config from mcp_config.json."""
    try:
        if MCP_CONFIG_PATH.exists():
            with open(MCP_CONFIG_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading mcp_config.json: {e}")
    return {"mcpServers": {}}


def save_mcp_config(config: dict) -> bool:
    """Save MCP config to mcp_config.json."""
    try:
        with open(MCP_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving mcp_config.json: {e}")
        return False


def remove_tools_from_cache(server_name: str) -> None:
    """Remove tools from cache when MCP server is disabled or deleted."""
    try:
        if not TOOLS_CACHE_PATH.exists():
            return
        
        with open(TOOLS_CACHE_PATH, 'r') as f:
            cache = json.load(f)
        
        if server_name in cache:
            del cache[server_name]
            
            with open(TOOLS_CACHE_PATH, 'w') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[{server_name}] Removed tools from cache")
    except Exception as e:
        logger.error(f"Failed to remove tools from cache: {e}")
