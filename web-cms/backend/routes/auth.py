"""
Authentication routes.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.config import CMS_PASSWORD, CMS_USERNAME, SESSION_DURATION_HOURS, logger
from backend.schemas.auth import LoginRequest
from backend.services.session import (
    check_rate_limit,
    create_session,
    destroy_session,
    get_client_ip,
    record_login_attempt,
    validate_session,
)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login")
async def login(request: Request, body: LoginRequest):
    client_ip = get_client_ip(request)
    allowed, wait_seconds = check_rate_limit(client_ip)
    
    if not allowed:
        logger.warning(f"Rate limited login attempt from {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Please wait {wait_seconds} seconds."
        )
    
    if body.username == CMS_USERNAME and body.password == CMS_PASSWORD:
        record_login_attempt(client_ip, True)
        token = create_session(body.username)
        response = JSONResponse({"success": True, "message": "Login successful"})
        response.set_cookie(
            key="session",
            value=token,
            path="/",
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=SESSION_DURATION_HOURS * 3600
        )
        return response
    else:
        record_login_attempt(client_ip, False)
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get("session")
    if token:
        destroy_session(token)
    response = JSONResponse({"success": True})
    response.delete_cookie(key="session", path="/")
    return response


@router.get("/auth/check")
async def auth_check(request: Request):
    token = request.cookies.get("session")
    is_auth = validate_session(token) if token else False
    return {"authenticated": is_auth}
