"""Configuration loading for MCP Xiaozhi."""

import json
import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Auto-load environment variables from a .env file if present
load_dotenv()

logger = logging.getLogger("MCP_PIPE")

# Reconnection settings
INITIAL_BACKOFF = 1  # Initial wait time in seconds
MAX_BACKOFF = 600  # Maximum wait time in seconds


def get_endpoint_url() -> Optional[str]:
    """Get MCP endpoint URL from environment.

    Returns:
        The endpoint URL or None if not set
    """
    return os.environ.get("MCP_ENDPOINT")


def load_config() -> Dict[str, Any]:
    """Load JSON config from $MCP_CONFIG or ./mcp_config.json.

    Returns:
        Configuration dictionary or empty dict if not found/invalid
    """
    path = os.environ.get("MCP_CONFIG") or os.path.join(os.getcwd(), "mcp_config.json")

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # Expand environment variables using the ${VAR} or $VAR format
            expanded_content = os.path.expandvars(content)
            return json.loads(expanded_content)
    except Exception as e:
        logger.warning(f"Failed to load config {path}: {e}")
        return {}


def get_enabled_servers(config: Dict[str, Any]) -> tuple[list[str], list[str]]:
    """Get enabled and disabled servers from config.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (enabled_servers, disabled_servers)
    """
    servers_cfg = config.get("mcpServers", {}) if isinstance(config, dict) else {}
    all_servers = list(servers_cfg.keys())

    enabled = [
        name for name, entry in servers_cfg.items()
        if not (entry or {}).get("disabled")
    ]
    disabled = [name for name in all_servers if name not in enabled]

    return enabled, disabled
