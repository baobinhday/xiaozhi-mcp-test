"""I/O piping functions for MCP Xiaozhi."""

import asyncio
import json
import logging
import sys
from subprocess import Popen
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import websockets

from .tools_filter import filter_tools_response, cache_tools_for_cms

logger = logging.getLogger("MCP_PIPE")

# Track pending tools/list requests to pass include_disabled flag to response
# Key: request_id, Value: include_disabled flag
_pending_tools_requests: dict[str, bool] = {}


async def pipe_websocket_to_process(
    websocket: "websockets.WebSocketClientProtocol",
    process: Popen,
    target: str,
) -> None:
    """Read data from WebSocket and write to process stdin.

    Args:
        websocket: WebSocket connection
        process: Subprocess to write to
        target: Server target name for logging
    """
    try:
        while True:
            # Read message from WebSocket
            message = await websocket.recv()
            logger.debug(f"[{target}] << {str(message)[:120]}...")

            # Write to process stdin (in text mode)
            if isinstance(message, bytes):
                message = message.decode("utf-8")
            
            # Track tools/list requests to capture include_disabled param
            try:
                msg = json.loads(message)
                if msg.get("method") == "tools/list":
                    request_id = msg.get("id")
                    include_disabled = msg.get("params", {}).get("include_disabled", False)
                    if request_id:
                        _pending_tools_requests[request_id] = include_disabled
                        logger.debug(f"[{target}] Tracking tools/list request {request_id} (include_disabled={include_disabled})")
            except json.JSONDecodeError:
                pass
            
            process.stdin.write(message + "\n")
            process.stdin.flush()
    except Exception as e:
        logger.error(f"[{target}] Error in WebSocket to process pipe: {e}")
        raise  # Re-throw exception to trigger reconnection
    finally:
        # Close process stdin
        if not process.stdin.closed:
            process.stdin.close()


async def pipe_process_to_websocket(
    process: Popen,
    websocket: "websockets.WebSocketClientProtocol",
    target: str,
) -> None:
    """Read data from process stdout and send to WebSocket.

    Args:
        process: Subprocess to read from
        websocket: WebSocket connection
        target: Server target name for logging
    """
    try:
        while True:
            # Read data from process stdout
            data = await asyncio.to_thread(process.stdout.readline)

            if not data:  # If no data, the process may have ended
                logger.info(f"[{target}] Process has ended output")
                break

            # Check if this is a tools/list response and filter it
            try:
                msg = json.loads(data)
                request_id = msg.get("id")
                
                # Check if this is a response to a tools/list request
                if request_id and "result" in msg and "tools" in msg.get("result", {}):
                    # Cache ALL tools (unfiltered) for CMS before filtering
                    tools = msg["result"]["tools"]
                    cache_tools_for_cms(target, tools)
                    
                    # Always filter: hub is pure pass-through, bridge handles all filtering
                    include_disabled = _pending_tools_requests.pop(request_id, False)
                    
                    # Filter the tools response for hub
                    data = filter_tools_response(data, target, include_disabled) + "\n"
                    logger.info(f"[{target}] Filtered tools response (include_disabled={include_disabled})")
            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.debug(f"[{target}] Error processing response: {e}")

            # Send data to WebSocket
            logger.debug(f"[{target}] >> {data[:120]}...")
            # In text mode, data is already a string, no need to decode
            await websocket.send(data)
    except Exception as e:
        logger.error(f"[{target}] Error in process to WebSocket pipe: {e}")
        raise  # Re-throw exception to trigger reconnection


async def pipe_process_stderr_to_terminal(process: Popen, target: str) -> None:
    """Read data from process stderr and print to terminal.

    Args:
        process: Subprocess to read stderr from
        target: Server target name for logging
    """
    try:
        while True:
            # Read data from process stderr
            data = await asyncio.to_thread(process.stderr.readline)

            if not data:  # If no data, the process may have ended
                logger.info(f"[{target}] Process has ended stderr output")
                break

            # Print stderr data to terminal (in text mode, data is already a string)
            sys.stderr.write(data)
            sys.stderr.flush()
    except Exception as e:
        logger.error(f"[{target}] Error in process stderr pipe: {e}")
        raise  # Re-throw exception to trigger reconnection
