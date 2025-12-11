"""SQLite database management for MCP endpoints.

This module provides CRUD operations for managing MCP endpoint configurations
stored in a SQLite database.
"""

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MCP_PIPE")

# Database file location
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DB_DIR / "app.db"

# Track if database has been initialized
_db_initialized = False


def get_connection() -> sqlite3.Connection:
    """Get a database connection.
    
    Returns:
        SQLite connection object
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the database schema.
    
    Creates the mcp_endpoints table if it doesn't exist.
    Only logs initialization message once.
    """
    global _db_initialized
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mcp_endpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Only log once
        if not _db_initialized:
            logger.info(f"Database initialized at {DB_PATH}")
            _db_initialized = True
    finally:
        conn.close()


def get_all_endpoints() -> List[Dict[str, Any]]:
    """Get all MCP endpoints.
    
    Returns:
        List of endpoint dictionaries
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mcp_endpoints ORDER BY id")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_enabled_endpoints() -> List[Dict[str, Any]]:
    """Get only enabled MCP endpoints.
    
    Returns:
        List of enabled endpoint dictionaries
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mcp_endpoints WHERE enabled = 1 ORDER BY id")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_endpoint_by_id(endpoint_id: int) -> Optional[Dict[str, Any]]:
    """Get a single endpoint by ID.
    
    Args:
        endpoint_id: The endpoint ID
        
    Returns:
        Endpoint dictionary or None if not found
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mcp_endpoints WHERE id = ?", (endpoint_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_endpoint(name: str, url: str, enabled: bool = True) -> Dict[str, Any]:
    """Add a new MCP endpoint.
    
    Args:
        name: Unique name for the endpoint
        url: WebSocket URL of the endpoint
        enabled: Whether the endpoint is enabled
        
    Returns:
        The created endpoint dictionary
        
    Raises:
        sqlite3.IntegrityError: If name already exists
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO mcp_endpoints (name, url, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, url, 1 if enabled else 0, now, now)
        )
        conn.commit()
        endpoint_id = cursor.lastrowid
        logger.info(f"Added endpoint: {name} ({url})")
        return get_endpoint_by_id(endpoint_id)
    finally:
        conn.close()


def update_endpoint(
    endpoint_id: int,
    name: Optional[str] = None,
    url: Optional[str] = None,
    enabled: Optional[bool] = None
) -> Optional[Dict[str, Any]]:
    """Update an existing MCP endpoint.
    
    Args:
        endpoint_id: The endpoint ID to update
        name: New name (optional)
        url: New URL (optional)
        enabled: New enabled status (optional)
        
    Returns:
        Updated endpoint dictionary or None if not found
    """
    existing = get_endpoint_by_id(endpoint_id)
    if not existing:
        return None
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if url is not None:
            updates.append("url = ?")
            params.append(url)
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)
        
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())
            params.append(endpoint_id)
            
            query = f"UPDATE mcp_endpoints SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            logger.info(f"Updated endpoint ID {endpoint_id}")
        
        return get_endpoint_by_id(endpoint_id)
    finally:
        conn.close()


def delete_endpoint(endpoint_id: int) -> bool:
    """Delete an MCP endpoint.
    
    Args:
        endpoint_id: The endpoint ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mcp_endpoints WHERE id = ?", (endpoint_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted endpoint ID {endpoint_id}")
        return deleted
    finally:
        conn.close()


def endpoint_count() -> int:
    """Get the total number of endpoints.
    
    Returns:
        Number of endpoints in the database
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM mcp_endpoints")
        return cursor.fetchone()[0]
    finally:
        conn.close()
