"""WebSocket connection handling for MCP Xiaozhi."""

import asyncio
import logging
import subprocess
from typing import Optional

import websockets

from .config import INITIAL_BACKOFF, MAX_BACKOFF
from .pipe import (
    pipe_process_stderr_to_terminal,
    pipe_process_to_websocket,
    pipe_websocket_to_process,
)
from .server_builder import build_server_command

logger = logging.getLogger("MCP_PIPE")


async def connect_with_retry(uri: str, target: str, endpoint_id: Optional[int] = None) -> None:
    """Connect to WebSocket server with retry mechanism.

    Args:
        uri: WebSocket endpoint URI
        target: Server target name
        endpoint_id: Optional endpoint ID for status tracking
    """
    from .database import update_endpoint_status
    
    reconnect_attempt = 0
    backoff = INITIAL_BACKOFF

    while True:  # Infinite reconnection
        try:
            if reconnect_attempt > 0:
                logger.info(
                    f"[{target}] Waiting {backoff}s before reconnection "
                    f"attempt {reconnect_attempt}..."
                )
                # Set status to disconnected while waiting
                if endpoint_id:
                    update_endpoint_status(endpoint_id, 'disconnected')
                await asyncio.sleep(backoff)

            # Attempt to connect
            await connect_to_server(uri, target, endpoint_id)

        except Exception as e:
            reconnect_attempt += 1
            logger.warning(
                f"[{target}] Connection closed (attempt {reconnect_attempt}): {e}"
            )
            # Set error status
            if endpoint_id:
                update_endpoint_status(endpoint_id, 'error', str(e))
            # Calculate wait time for next reconnection (exponential backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)


from urllib.parse import urlparse
import os

async def connect_to_server(uri: str, target: str, endpoint_id: Optional[int] = None) -> None:
    """Connect to WebSocket server and pipe stdio.

    Args:
        uri: WebSocket endpoint URI
        target: Server target name
        endpoint_id: Optional endpoint ID for status tracking
    """
    from .database import update_endpoint_status
    
    process: Optional[subprocess.Popen] = None

    try:
        # Auto-fix URI if missing /mcp path (common configuration error)
        parsed = urlparse(uri)
        if parsed.path == "" or parsed.path == "/":
            logger.warning(f"[{target}] Endpoint URL '{uri}' missing '/mcp' path. Appending automatically.")
            uri = uri.rstrip("/") + "/mcp"

        logger.info(f"[{target}] Connecting to WebSocket server...")
        
        # Set status to connecting
        if endpoint_id:
            update_endpoint_status(endpoint_id, 'connecting')

        # Build WebSocket URI with server name for hub identification
        ws_uri = (
            f"{uri}?server={target}"
            if "?" not in uri
            else f"{uri}&server={target}"
        )
        
        # Add MCP authentication token if configured
        mcp_ws_token = os.environ.get("MCP_WS_TOKEN", "")
        if mcp_ws_token:
            ws_uri = f"{ws_uri}&token={mcp_ws_token}"

        async with websockets.connect(ws_uri) as websocket:
            logger.info(f"[{target}] Successfully connected to WebSocket server")
            
            # Set status to connected
            if endpoint_id:
                update_endpoint_status(endpoint_id, 'connected')

            # Start server process (built from CLI arg or config)
            cmd, env = build_server_command(target)
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                text=True,
                env=env,
            )
            logger.info(f"[{target}] Started server process: {' '.join(cmd)}")

            # Create tasks for bidirectional communication
            await asyncio.gather(
                pipe_websocket_to_process(websocket, process, target),
                pipe_process_to_websocket(process, websocket, target),
                pipe_process_stderr_to_terminal(process, target),
            )

    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"[{target}] WebSocket connection closed: {e}")
        if endpoint_id:
            update_endpoint_status(endpoint_id, 'disconnected')
        raise  # Re-throw exception to trigger reconnection

    except Exception as e:
        logger.error(f"[{target}] Connection error: {e}")
        if endpoint_id:
            update_endpoint_status(endpoint_id, 'error', str(e))
        raise  # Re-throw exception

    finally:
        # Ensure the child process is properly terminated
        if process is not None:
            logger.info(f"[{target}] Terminating server process")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            logger.info(f"[{target}] Server process terminated")
