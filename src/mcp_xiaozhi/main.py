"""Main entry point for MCP Xiaozhi."""

import asyncio
import os
import signal
import sys
from typing import Optional

from .config import get_all_endpoint_urls, get_config_mtime, get_enabled_servers, load_config
from .connection import connect_with_retry
from .tools_filter import remove_tools_from_cache
from .utils import setup_logging

logger = setup_logging()

# Polling interval for checking new endpoints (in seconds)
ENDPOINT_POLL_INTERVAL = 10


def signal_handler(sig: int, frame) -> None:
    """Handle interrupt signals.

    Args:
        sig: Signal number
        frame: Current stack frame
    """
    logger.info("Received interrupt signal, shutting down...")
    sys.exit(0)


async def _run_server_for_endpoint(endpoint_url: str, endpoint_name: str, server: str) -> None:
    """Run a single MCP server for an endpoint.

    Args:
        endpoint_url: WebSocket URL for the endpoint
        endpoint_name: Name of the endpoint (for logging)
        server: Server name to run
    """
    from .database import get_endpoint_by_name
    
    logger.info(f"[{endpoint_name}] Starting server '{server}' -> {endpoint_url}")
    
    # Look up endpoint ID for status tracking
    endpoint = get_endpoint_by_name(endpoint_name)
    endpoint_id = endpoint["id"] if endpoint else None
    
    await connect_with_retry(endpoint_url, server, endpoint_id)


async def _wait_for_endpoints() -> list[dict]:
    """Wait for endpoints to be configured.
    
    Polls the database every ENDPOINT_POLL_INTERVAL seconds until
    at least one endpoint is available.
    
    Returns:
        List of endpoint dictionaries
    """
    logger.info(f"No endpoints configured. Waiting for endpoints... (check every {ENDPOINT_POLL_INTERVAL}s)")
    logger.info("Add endpoints via CMS at http://localhost:8890")
    
    while True:
        await asyncio.sleep(ENDPOINT_POLL_INTERVAL)
        endpoints = get_all_endpoint_urls()
        if endpoints:
            logger.info(f"Found {len(endpoints)} new endpoint(s)!")
            return endpoints


async def _run_servers(target_arg: Optional[str]) -> None:
    """Run MCP servers across all configured endpoints.

    Args:
        target_arg: Optional specific target to run
    """
    # Track running tasks: key = "endpoint_name:server_name", value = asyncio.Task
    running_tasks: dict[str, asyncio.Task] = {}
    
    # Load MCP servers config and track modification time for hot-reloading
    cfg = load_config()
    config_mtime = get_config_mtime()
    enabled, disabled = get_enabled_servers(cfg)
    
    if disabled:
        logger.info(f"Skipping disabled servers: {', '.join(disabled)}")
        # Clean up cache for disabled servers on startup
        for server_name in disabled:
            remove_tools_from_cache(server_name)
    
    if not enabled and not target_arg:
        raise RuntimeError("No enabled mcpServers found in config")
    
    if not target_arg:
        logger.info(f"Will start servers: {', '.join(enabled)}")
    
    # Track known endpoints
    known_endpoints: dict[str, str] = {}  # name -> url
    
    while True:
        config_changed = False
        
        # Check if config file has changed (hot-reload)
        new_mtime = get_config_mtime()
        if new_mtime > config_mtime:
            logger.info("🔄 Config file changed, performing hot-reload...")
            config_mtime = new_mtime
            cfg = load_config()
            new_enabled, new_disabled = get_enabled_servers(cfg)
            
            # Log changes
            added_servers = set(new_enabled) - set(enabled)
            removed_servers = set(enabled) - set(new_enabled)
            
            if added_servers:
                logger.info(f"➕ New servers: {', '.join(added_servers)}")
            if removed_servers:
                logger.info(f"➖ Servers removed/disabled: {', '.join(removed_servers)}")
            
            # Cancel tasks for removed/disabled servers
            tasks_to_cancel = []
            for task_key, task in list(running_tasks.items()):
                # task_key format: "endpoint_name:server_name"
                parts = task_key.split(":", 1)
                if len(parts) == 2:
                    server_name = parts[1]
                    if server_name in removed_servers:
                        tasks_to_cancel.append((task_key, task))
            
            for task_key, task in tasks_to_cancel:
                logger.info(f"🛑 Stopping: {task_key}")
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                del running_tasks[task_key]
            
            # Remove tools from cache for disabled servers
            for server_name in removed_servers:
                remove_tools_from_cache(server_name)
            
            enabled = new_enabled
            disabled = new_disabled
            config_changed = True
            
            if new_disabled:
                logger.info(f"Skipping disabled servers: {', '.join(new_disabled)}")
            if enabled:
                logger.info(f"✅ Active servers: {', '.join(enabled)}")
        
        # Get current endpoints from database
        endpoints = get_all_endpoint_urls()
        
        if not endpoints:
            # Wait for endpoints to be added
            endpoints = await _wait_for_endpoints()
        
        # Build current endpoint map
        current_endpoints = {ep["name"]: ep["url"] for ep in endpoints}
        
        # Find new endpoints or endpoints that need server updates
        for endpoint in endpoints:
            endpoint_name = endpoint["name"]
            endpoint_url = endpoint["url"]
            
            is_new_endpoint = endpoint_name not in known_endpoints
            
            if is_new_endpoint:
                known_endpoints[endpoint_name] = endpoint_url
                logger.info(f"📡 New endpoint: {endpoint_name} -> {endpoint_url}")
            
            # Start servers for new endpoints OR start newly added servers for existing endpoints
            if not target_arg:
                for server in enabled:
                    task_key = f"{endpoint_name}:{server}"
                    
                    # Start task if not already running
                    if task_key not in running_tasks or running_tasks[task_key].done():
                        task = asyncio.create_task(
                            _run_server_for_endpoint(endpoint_url, endpoint_name, server)
                        )
                        running_tasks[task_key] = task
                        if not is_new_endpoint and config_changed:
                            logger.info(f"🚀 Starting: {task_key}")
            else:
                # Run specific target
                task_key = f"{endpoint_name}:custom"
                if task_key not in running_tasks or running_tasks[task_key].done():
                    if os.path.exists(target_arg):
                        task = asyncio.create_task(connect_with_retry(endpoint_url, target_arg))
                        running_tasks[task_key] = task
                    else:
                        logger.error(
                            "Argument must be a local Python script path. "
                            "To run configured servers, run without arguments."
                        )
                        sys.exit(1)
        
        # Clean up completed/failed tasks
        for task_key in list(running_tasks.keys()):
            if running_tasks[task_key].done():
                # Check if it failed
                try:
                    running_tasks[task_key].result()
                except Exception as e:
                    logger.warning(f"Task {task_key} failed: {e}")
                del running_tasks[task_key]
        
        # Wait a bit before checking again
        await asyncio.sleep(ENDPOINT_POLL_INTERVAL)


def main() -> None:
    """Main entry point for mcp-pipe command."""
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Determine target: default to all if no arg; single target otherwise
    target_arg = sys.argv[1] if len(sys.argv) >= 2 else None

    try:
        asyncio.run(_run_servers(target_arg))
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Program execution error: {e}")


if __name__ == "__main__":
    main()


