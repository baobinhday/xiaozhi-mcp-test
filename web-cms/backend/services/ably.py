import os
import asyncio
from ably import AblyRest
from backend.config import logger

class AblyService:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AblyService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.api_key = os.getenv("ABLY_API_KEY")
        if not self.api_key:
            logger.warning("ABLY_API_KEY not found. Real-time updates via Ably will be disabled.")
            self._client = None
        else:
            try:
                self._client = AblyRest(self.api_key)
                logger.info("Ably service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Ably: {e}")
                self._client = None
    
    async def publish_endpoint_update(self, action: str, endpoint_data: dict):
        """
        Publish an endpoint update event.
        
        Args:
            action: One of 'CONNECT', 'DISCONNECT', 'UPDATE'
            endpoint_data: Dictionary containing endpoint details (id, name, url)
        """
        if not self._client:
            return

        channel = self._client.channels.get('mcp-commands')
        
        payload = {
            "action": action,
            "endpoint": endpoint_data
        }
        
        try:
            # AblyRest publish is synchronous or async depending on usage, 
            # but AblyRest is typically synchronous. However, ably-python's AblyRest 
            # might make HTTP requests. 
            # Actually AblyRest in ably-python 2.x is async? 
            # Let's check documentation or assume async for now as we are in FastAPI.
            # Wait, ably-python 2.0+ supports async with AblyRest? 
            # Usually AblyRealtime is async, AblyRest might be sync or async.
            # Looking at docs, AblyRest.publish is async.
            await channel.publish('update', payload)
            logger.info(f"Published Ably event: {action} for {endpoint_data.get('name')}")
        except Exception as e:
            logger.error(f"Failed to publish Ably event: {e}")

ably_service = AblyService()
