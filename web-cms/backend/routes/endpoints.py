"""
Endpoints CRUD routes.
"""

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sse_starlette.sse import EventSourceResponse

from backend.config import logger
from backend.dependencies import require_auth
from backend.schemas.endpoints import EndpointCreate, EndpointUpdate
from backend.services.session import validate_session

from backend.services.ably import ably_service


# Import database functions - add parent to path if needed
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.mcp_xiaozhi.database import (
    add_endpoint,
    delete_endpoint,
    get_all_endpoints,
    get_connection,
    get_endpoint_by_id,
    update_endpoint,
)

router = APIRouter(prefix="/api", tags=["endpoints"])


@router.get("/endpoints/stream")
async def endpoints_stream(request: Request, session: str = Cookie(None)):
    """SSE endpoint for streaming endpoint status updates."""
    if not session or not validate_session(session):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async def event_generator():
        try:
            # Send initial data immediately
            endpoints = get_all_endpoints()
            yield {"data": json.dumps({"endpoints": endpoints})}
            
            # Keep streaming updates every 10 seconds
            while True:
                await asyncio.sleep(10)
                
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("SSE client disconnected")
                    break
                
                endpoints = get_all_endpoints()
                yield {"data": json.dumps({"endpoints": endpoints})}
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled")
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
    
    return EventSourceResponse(event_generator())


@router.get("/endpoints")
async def list_endpoints(_: str = Depends(require_auth)):
    endpoints = get_all_endpoints()
    return {"endpoints": endpoints}


@router.get("/endpoints/{endpoint_id}")
async def get_endpoint(endpoint_id: int, _: str = Depends(require_auth)):
    endpoint = get_endpoint_by_id(endpoint_id)
    if endpoint:
        return endpoint
    raise HTTPException(status_code=404, detail="Not found")

@router.post("/endpoints", status_code=201)
async def create_endpoint_route(body: EndpointCreate, _: str = Depends(require_auth)):
    if not body.name.strip() or not body.url.strip():
        raise HTTPException(status_code=400, detail="Name and URL are required")
    
    try:
        endpoint = add_endpoint(body.name.strip(), body.url.strip(), body.enabled)
        
        # Publish connect event if enabled
        if endpoint["enabled"]:
            await ably_service.publish_endpoint_update("CONNECT", endpoint)
            
        return endpoint
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/endpoints/{endpoint_id}")
async def update_endpoint_route(endpoint_id: int, body: EndpointUpdate, _: str = Depends(require_auth)):
    # Get current state to detect changes
    current = get_endpoint_by_id(endpoint_id)
    if not current:
        raise HTTPException(status_code=404, detail="Not found")

    endpoint = update_endpoint(
        endpoint_id,
        name=body.name,
        url=body.url,
        enabled=body.enabled
    )
    if endpoint:
        # Determine notification action
        if endpoint["enabled"] and not current["enabled"]:
            # Just enabled
            await ably_service.publish_endpoint_update("CONNECT", endpoint)
        elif not endpoint["enabled"] and current["enabled"]:
            # Just disabled
            await ably_service.publish_endpoint_update("DISCONNECT", endpoint)
        elif endpoint["enabled"] and (current["url"] != endpoint["url"] or current["name"] != endpoint["name"]):
            # URL or name changed while enabled - treat as update/reconnect
            # Note: The subscriber should handle 'UPDATE' by reconnecting if URL changed
            await ably_service.publish_endpoint_update("UPDATE", endpoint)

        return endpoint
    raise HTTPException(status_code=404, detail="Not found")


@router.delete("/endpoints/{endpoint_id}")
async def delete_endpoint_route(endpoint_id: int, _: str = Depends(require_auth)):
    # Get endpoint before deleting to notify
    endpoint = get_endpoint_by_id(endpoint_id)
    
    if delete_endpoint(endpoint_id):
        if endpoint and endpoint["enabled"]:
            await ably_service.publish_endpoint_update("DISCONNECT", endpoint)
        return {"success": True}
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/backup")
async def backup_endpoints(_: str = Depends(require_auth)):
    endpoints = get_all_endpoints()
    backup_data = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "endpoints": endpoints
    }
    return Response(
        content=json.dumps(backup_data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=mcp_endpoints_backup.json"}
    )


@router.post("/restore")
async def restore_endpoints(request: Request, _: str = Depends(require_auth)):
    body = await request.json()
    endpoints_data = body.get("endpoints", [])
    
    if not endpoints_data:
        raise HTTPException(status_code=400, detail="No endpoints data provided")
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mcp_endpoints")
        
        for ep in endpoints_data:
            cursor.execute(
                """
                INSERT INTO mcp_endpoints (name, url, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    ep.get("name", "Unnamed"),
                    ep.get("url", ""),
                    1 if ep.get("enabled", True) else 0,
                    ep.get("created_at", datetime.now(timezone.utc).isoformat()),
                    datetime.now(timezone.utc).isoformat()
                )
            )
        
        conn.commit()
        logger.info(f"Restored {len(endpoints_data)} endpoints from backup")
        return {"success": True, "restored": len(endpoints_data)}
    finally:
        conn.close()
