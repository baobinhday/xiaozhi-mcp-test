"""
Session management service.

Handles session creation, validation, destruction, and rate limiting.
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request

from backend.config import (
    MAX_LOGIN_ATTEMPTS,
    RATE_LIMIT_WINDOW,
    SESSION_DURATION_HOURS,
    logger,
)

# In-memory session storage
sessions = {}

# Rate limiting storage
# Dict: ip -> {"count": int, "first_attempt": datetime, "last_failed": datetime}
login_attempts = {}


def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)


def create_session(username: str) -> str:
    """Create a new session for a user."""
    token = generate_session_token()
    sessions[token] = {
        "username": username,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)
    }
    return token


def validate_session(token: str) -> bool:
    """Validate a session token."""
    if not token or token not in sessions:
        return False
    
    session = sessions[token]
    if datetime.now(timezone.utc) > session["expires_at"]:
        del sessions[token]
        return False
    
    return True


def destroy_session(token: str) -> bool:
    """Destroy a session."""
    if token in sessions:
        del sessions[token]
        return True
    return False


def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str) -> tuple:
    """Check if IP is rate limited. Returns (allowed, wait_seconds)."""
    if ip not in login_attempts:
        return True, 0
    
    attempt = login_attempts[ip]
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    
    if attempt["first_attempt"] < window_start:
        del login_attempts[ip]
        return True, 0
    
    if attempt["count"] >= MAX_LOGIN_ATTEMPTS:
        backoff = min(2 ** (attempt["count"] - MAX_LOGIN_ATTEMPTS + 1), 300)
        wait_until = attempt["last_failed"] + timedelta(seconds=backoff)
        if now < wait_until:
            return False, int((wait_until - now).total_seconds()) + 1
    
    return True, 0


def record_login_attempt(ip: str, success: bool):
    """Record a login attempt."""
    now = datetime.now(timezone.utc)
    if success:
        login_attempts.pop(ip, None)
    else:
        if ip not in login_attempts:
            login_attempts[ip] = {"count": 0, "first_attempt": now, "last_failed": now}
        login_attempts[ip]["count"] += 1
        login_attempts[ip]["last_failed"] = now
        logger.warning(f"Failed login attempt from {ip} (count: {login_attempts[ip]['count']})")
