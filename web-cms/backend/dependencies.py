"""
FastAPI dependencies for authentication.
"""

from typing import Optional

from fastapi import Cookie, HTTPException, Request

from backend.services.session import validate_session


async def get_session_token(request: Request) -> Optional[str]:
    """Extract session token from cookies."""
    return request.cookies.get("session")


async def require_auth(request: Request, session: Optional[str] = Cookie(None, alias="session")):
    """Require authentication for this route."""
    if not session or not validate_session(session):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return session
