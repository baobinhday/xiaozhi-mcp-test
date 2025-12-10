"""Main entry point for MCP Xiaozhi."""

import asyncio
import os
import signal
import sys
from typing import Optional

from .config import get_enabled_servers, get_endpoint_url, load_config
from .connection import connect_with_retry
from .utils import setup_logging

logger = setup_logging()


def signal_handler(sig: int, frame) -> None:
    """Handle interrupt signals.

    Args:
        sig: Signal number
        frame: Current stack frame
    """
    logger.info("Received interrupt signal, shutting down...")
    sys.exit(0)


async def _run_servers(endpoint_url: str, target_arg: Optional[str]) -> None:
    """Run MCP servers.

    Args:
        endpoint_url: WebSocket endpoint URL
        target_arg: Optional specific target to run
    """
    if not target_arg:
        # Run all enabled servers from config
        cfg = load_config()
        enabled, disabled = get_enabled_servers(cfg)

        if disabled:
            logger.info(f"Skipping disabled servers: {', '.join(disabled)}")

        if not enabled:
            raise RuntimeError("No enabled mcpServers found in config")

        logger.info(f"Starting servers: {', '.join(enabled)}")
        tasks = [
            asyncio.create_task(connect_with_retry(endpoint_url, t))
            for t in enabled
        ]
        # Run all forever; if any crashes it will auto-retry inside
        await asyncio.gather(*tasks)
    else:
        # Run specific target
        if os.path.exists(target_arg):
            await connect_with_retry(endpoint_url, target_arg)
        else:
            logger.error(
                "Argument must be a local Python script path. "
                "To run configured servers, run without arguments."
            )
            sys.exit(1)


def main() -> None:
    """Main entry point for mcp-pipe command."""
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Get endpoint from environment
    endpoint_url = get_endpoint_url()
    if not endpoint_url:
        logger.error("Please set the `MCP_ENDPOINT` environment variable")
        sys.exit(1)

    # Determine target: default to all if no arg; single target otherwise
    target_arg = sys.argv[1] if len(sys.argv) >= 2 else None

    try:
        asyncio.run(_run_servers(endpoint_url, target_arg))
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Program execution error: {e}")


if __name__ == "__main__":
    main()
