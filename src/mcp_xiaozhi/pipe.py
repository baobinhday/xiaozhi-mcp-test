"""I/O piping functions for MCP Xiaozhi."""

import asyncio
import logging
import sys
from subprocess import Popen
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import websockets

logger = logging.getLogger("MCP_PIPE")


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
