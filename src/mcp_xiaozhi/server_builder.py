"""Server command builder for MCP Xiaozhi."""

import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

from .config import load_config
from .utils import ConfigurationError

logger = logging.getLogger("MCP_PIPE")


def build_server_command(target: Optional[str] = None) -> Tuple[List[str], Dict[str, str]]:
    """Build command and environment for the server process.

    Priority:
    - If target matches a server in config.mcpServers: use its definition
    - Else: treat target as a Python script path (back-compat)

    Args:
        target: Server name from config or path to Python script.
                If None, reads from sys.argv[1].

    Returns:
        Tuple of (command_list, environment_dict)

    Raises:
        ConfigurationError: If configuration is invalid
        RuntimeError: If target is not found
    """
    if target is None:
        if len(sys.argv) < 2:
            raise ConfigurationError("Missing server name or script path")
        target = sys.argv[1]

    cfg = load_config()
    servers = cfg.get("mcpServers", {}) if isinstance(cfg, dict) else {}

    if target in servers:
        return _build_from_config(target, servers[target])

    # Fallback to script path (back-compat)
    return _build_from_script(target)


def _build_from_config(
    target: str,
    entry: Optional[Dict],
) -> Tuple[List[str], Dict[str, str]]:
    """Build command from MCP config entry.

    Args:
        target: Server name
        entry: Server configuration entry

    Returns:
        Tuple of (command_list, environment_dict)
    """
    entry = entry or {}

    if entry.get("disabled"):
        raise ConfigurationError(f"Server '{target}' is disabled in config")

    typ = (entry.get("type") or entry.get("transportType") or "stdio").lower()

    # Environment for child process
    child_env = os.environ.copy()
    for k, v in (entry.get("env") or {}).items():
        child_env[str(k)] = str(v)

    if typ == "stdio":
        return _build_stdio_command(target, entry, child_env)

    if typ in ("sse", "http", "streamablehttp"):
        return _build_http_command(target, entry, typ, child_env)

    raise ConfigurationError(f"Unsupported server type: {typ}")


def _build_stdio_command(
    target: str,
    entry: Dict,
    child_env: Dict[str, str],
) -> Tuple[List[str], Dict[str, str]]:
    """Build stdio transport command."""
    command = entry.get("command")
    args = entry.get("args") or []

    if not command:
        raise ConfigurationError(f"Server '{target}' is missing 'command'")

    return [command, *args], child_env


def _build_http_command(
    target: str,
    entry: Dict,
    typ: str,
    child_env: Dict[str, str],
) -> Tuple[List[str], Dict[str, str]]:
    """Build HTTP/SSE transport command using mcp-proxy."""
    url = entry.get("url")

    if not url:
        raise ConfigurationError(f"Server '{target}' (type {typ}) is missing 'url'")

    # Use current Python to run mcp-proxy module
    cmd = [sys.executable, "-m", "mcp_proxy"]

    if typ in ("http", "streamablehttp"):
        cmd += ["--transport", "streamablehttp"]

    # Optional headers: {"Authorization": "Bearer xxx"}
    headers = entry.get("headers") or {}
    for hk, hv in headers.items():
        cmd += ["-H", hk, str(hv)]

    cmd.append(url)
    return cmd, child_env


def _build_from_script(target: str) -> Tuple[List[str], Dict[str, str]]:
    """Build command from script path (backward compatibility).

    Args:
        target: Path to Python script

    Returns:
        Tuple of (command_list, environment_dict)
    """
    if not os.path.exists(target):
        raise RuntimeError(
            f"'{target}' is neither a configured server nor an existing script"
        )

    return [sys.executable, target], os.environ.copy()
