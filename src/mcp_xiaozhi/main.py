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
    
    try:
        await connect_with_retry(endpoint_url, server, endpoint_id)
    except RuntimeError as e:
        # Authentication errors are raised as RuntimeError - handle gracefully
        if "Authentication failed" in str(e):
            logger.warning(f"[{endpoint_name}:{server}] Stopped due to authentication failure")
        else:
            raise


from .ably_listener import AblyListener

async def _stop_endpoint(endpoint_name: str, running_tasks: dict, known_endpoints: dict) -> None:
    """Stop all servers for a specific endpoint."""
    logger.info(f"🛑 Stopping endpoint: {endpoint_name}")
    
    tasks_to_cancel = []
    for task_key in list(running_tasks.keys()):
        if task_key.startswith(f"{endpoint_name}:"):
            tasks_to_cancel.append(task_key)
    
    for task_key in tasks_to_cancel:
        task = running_tasks[task_key]
        logger.info(f"🛑 Stopping task: {task_key}")
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        del running_tasks[task_key]
    
    if endpoint_name in known_endpoints:
        del known_endpoints[endpoint_name]


async def _start_endpoint(
    endpoint_name: str, 
    endpoint_url: str, 
    running_tasks: dict, 
    known_endpoints: dict,
    enabled_servers: list,
    target_arg: Optional[str] = None
) -> None:
    """Start servers for a specific endpoint."""
    known_endpoints[endpoint_name] = endpoint_url
    
    if target_arg:
        # Run specific target
        task_key = f"{endpoint_name}:custom"
        if task_key not in running_tasks or running_tasks[task_key].done():
            if os.path.exists(target_arg):
                task = asyncio.create_task(connect_with_retry(endpoint_url, target_arg))
                running_tasks[task_key] = task
                logger.info(f"🚀 Started custom target for {endpoint_name}")
            else:
                logger.error("Target script not found")
        return

    # Start configured servers
    for server in enabled_servers:
        task_key = f"{endpoint_name}:{server}"
        if task_key not in running_tasks or running_tasks[task_key].done():
            task = asyncio.create_task(
                _run_server_for_endpoint(endpoint_url, endpoint_name, server)
            )
            running_tasks[task_key] = task
            logger.info(f"🚀 Started {server} for {endpoint_name}")


async def _run_servers(target_arg: Optional[str]) -> None:
    """Run MCP servers across all configured endpoints.

    Args:
        target_arg: Optional specific target to run
    """
    # Track running tasks: key = "endpoint_name:server_name", value = asyncio.Task
    running_tasks: dict[str, asyncio.Task] = {}
    
    # Track known endpoints
    known_endpoints: dict[str, str] = {}  # name -> url
    
    # Load MCP servers config and track modification time for hot-reloading
    cfg = load_config()
    config_mtime = get_config_mtime()
    enabled, disabled = get_enabled_servers(cfg)
    
    if disabled:
        logger.info(f"Skipping disabled servers: {', '.join(disabled)}")
        for server_name in disabled:
            remove_tools_from_cache(server_name)
    
    if not enabled and not target_arg:
        raise RuntimeError("No enabled mcpServers found in config")
    
    if not target_arg:
        logger.info(f"Will start servers: {', '.join(enabled)}")

    # Callback for Ably updates
    async def on_endpoint_update(action: str, endpoint: dict):
        name = endpoint.get("name")
        url = endpoint.get("url")
        
        if not name:
            return

        if action == "CONNECT":
            logger.info(f"🔔 Ably Connect: {name}")
            if name in known_endpoints:
                # Already connected, check if URL changed
                if known_endpoints[name] != url:
                    await _stop_endpoint(name, running_tasks, known_endpoints)
                    await _start_endpoint(name, url, running_tasks, known_endpoints, enabled, target_arg)
            else:
                await _start_endpoint(name, url, running_tasks, known_endpoints, enabled, target_arg)
                
        elif action == "DISCONNECT":
            logger.info(f"🔔 Ably Disconnect: {name}")
            await _stop_endpoint(name, running_tasks, known_endpoints)
            
        elif action == "UPDATE":
            logger.info(f"🔔 Ably Update: {name}")
            # Restart if connected
            if name in known_endpoints:
                await _stop_endpoint(name, running_tasks, known_endpoints)
            await _start_endpoint(name, url, running_tasks, known_endpoints, enabled, target_arg)

    # Start Ably Listener
    ably_listener = AblyListener(on_endpoint_update)
    await ably_listener.start()

    # Initial Sync with DB
    endpoints = get_all_endpoint_urls()
    if endpoints:
        logger.info(f"Initial sync: Found {len(endpoints)} endpoints")
        for ep in endpoints:
            await _start_endpoint(ep["name"], ep["url"], running_tasks, known_endpoints, enabled, target_arg)
    else:
        logger.info("No endpoints found in initial sync. Waiting for Ably updates...")

    # Main loop - only checks for config changes now
    while True:
        try:
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
                # Start new servers for ALL known endpoints
                if added_servers and not target_arg:
                    for ep_name, ep_url in known_endpoints.items():
                        for server in added_servers:
                             task_key = f"{ep_name}:{server}"
                             if task_key not in running_tasks:
                                task = asyncio.create_task(
                                    _run_server_for_endpoint(ep_url, ep_name, server)
                                )
                                running_tasks[task_key] = task
                                logger.info(f"🚀 Starting new server {server} for {ep_name}")

            # Clean up completed/failed tasks
            for task_key in list(running_tasks.keys()):
                if running_tasks[task_key].done():
                    # Check if it failed
                    try:
                        running_tasks[task_key].result()
                    except Exception as e:
                        logger.warning(f"Task {task_key} failed: {e}")
                    del running_tasks[task_key]
            
            # Wait a bit
            await asyncio.sleep(ENDPOINT_POLL_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
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


