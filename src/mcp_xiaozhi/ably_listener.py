import os
import asyncio
import logging
from typing import Callable, Awaitable
from ably import AblyRealtime

logger = logging.getLogger("MCP_PIPE")

class AblyListener:
    def __init__(self, on_update: Callable[[str, dict], Awaitable[None]]):
        """
        Args:
            on_update: Async callback function(action, endpoint_data)
        """
        self.api_key = os.getenv("ABLY_API_KEY")
        self.on_update = on_update
        self.client = None
        
    async def start(self):
        if not self.api_key:
            logger.warning("ABLY_API_KEY not found. Real-time updates via Ably will be disabled.")
            return

        try:
            self.client = AblyRealtime(self.api_key)
            channel = self.client.channels.get('mcp-commands')
            await channel.subscribe('update', self._handle_message)
            logger.info("📡 Listening for real-time updates via Ably")
        except Exception as e:
            logger.error(f"Failed to start Ably listener: {e}")

    async def _handle_message(self, message):
        try:
            data = message.data
            action = data.get('action')
            endpoint = data.get('endpoint')
            
            if action and endpoint:
                logger.info(f"📨 Received Ably event: {action} for {endpoint.get('name')}")
                await self.on_update(action, endpoint)
        except Exception as e:
            logger.error(f"Error handling Ably message: {e}")

    async def close(self):
        if self.client:
            await self.client.close()
            self.client = None
