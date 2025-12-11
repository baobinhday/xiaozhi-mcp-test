"""Main entry point for MCP Xiaozhi."""

import asyncio
import os
import signal
import sys
from typing import Optional, Set

from .config import get_all_endpoint_urls, get_enabled_servers, load_config
from .connection import connect_with_retry
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


async def _run_servers_for_endpoint(endpoint: dict, servers: list[str]) -> None:
    """Run MCP servers for a single endpoint.

    Args:
        endpoint: Dict with 'name' and 'url' keys
        servers: List of server names to run
    """
    endpoint_name = endpoint["name"]
    endpoint_url = endpoint["url"]
    
    logger.info(f"[{endpoint_name}] Starting {len(servers)} servers -> {endpoint_url}")
    
    tasks = [
        asyncio.create_task(connect_with_retry(endpoint_url, server))
        for server in servers
    ]
    await asyncio.gather(*tasks)


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
    # Track which endpoints are currently running
    active_endpoints: Set[str] = set()
    running_tasks: dict[str, asyncio.Task] = {}
    
    # Load MCP servers config once
    cfg = load_config()
    enabled, disabled = get_enabled_servers(cfg)
    
    if disabled:
        logger.info(f"Skipping disabled servers: {', '.join(disabled)}")
    
    if not enabled and not target_arg:
        raise RuntimeError("No enabled mcpServers found in config")
    
    if not target_arg:
        logger.info(f"Will start servers: {', '.join(enabled)}")
    
    while True:
        # Get current endpoints from database
        endpoints = get_all_endpoint_urls()
        
        if not endpoints:
            # Wait for endpoints to be added
            endpoints = await _wait_for_endpoints()
        
        # Find new endpoints that aren't running yet
        current_endpoint_names = {ep["name"] for ep in endpoints}
        new_endpoints = [ep for ep in endpoints if ep["name"] not in active_endpoints]
        
        if new_endpoints:
            logger.info(f"Found {len(endpoints)} endpoint(s): {', '.join(ep['name'] for ep in endpoints)}")
            
            for endpoint in new_endpoints:
                active_endpoints.add(endpoint["name"])
                
                if not target_arg:
                    # Run all enabled servers for this endpoint
                    task = asyncio.create_task(_run_servers_for_endpoint(endpoint, enabled))
                else:
                    # Run specific target
                    if os.path.exists(target_arg):
                        task = asyncio.create_task(connect_with_retry(endpoint["url"], target_arg))
                    else:
                        logger.error(
                            "Argument must be a local Python script path. "
                            "To run configured servers, run without arguments."
                        )
                        sys.exit(1)
                
                running_tasks[endpoint["name"]] = task
        
        # Wait a bit before checking for new endpoints again
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


