"""SQLite database management for MCP endpoints and tool settings.

This module provides CRUD operations for managing MCP endpoint configurations
and tool settings (enable/disable, custom metadata) stored in a SQLite database.
"""

import json
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
    
    Creates the mcp_endpoints and mcp_tool_settings tables if they don't exist.
    Migrates data from tools_config.json if it exists.
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
                connection_status TEXT DEFAULT 'disconnected',
                last_connected_at TEXT,
                connection_error TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create tool settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mcp_tool_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                custom_name TEXT,
                custom_description TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(server_name, tool_name)
            )
        """)
        
        conn.commit()
        
        # Migrate existing databases to add new columns
        _migrate_add_status_columns(cursor, conn)
        
        # Only log once
        if not _db_initialized:
            logger.info(f"Database initialized at {DB_PATH}")
            _db_initialized = True
            
            # Migrate from tools_config.json if it exists
            _migrate_tools_config_from_json()
    finally:
        conn.close()


def _migrate_add_status_columns(cursor: sqlite3.Cursor, conn: sqlite3.Connection) -> None:
    """Add connection status columns to existing mcp_endpoints table (migration)."""
    try:
        # Check if connection_status column exists
        cursor.execute("PRAGMA table_info(mcp_endpoints)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'connection_status' not in columns:
            logger.info("Migrating database: adding connection status columns")
            cursor.execute("ALTER TABLE mcp_endpoints ADD COLUMN connection_status TEXT DEFAULT 'disconnected'")
            cursor.execute("ALTER TABLE mcp_endpoints ADD COLUMN last_connected_at TEXT")
            cursor.execute("ALTER TABLE mcp_endpoints ADD COLUMN connection_error TEXT")
            conn.commit()
            logger.info("Migration complete: connection status columns added")
    except Exception as e:
        logger.error(f"Failed to migrate database: {e}")


def _migrate_tools_config_from_json() -> None:
    """Migrate data from tools_config.json to database (one-time migration)."""
    json_path = DB_DIR / "tools_config.json"
    
    if not json_path.exists():
        return
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        disabled_tools = config.get("disabledTools", {})
        custom_tools = config.get("customTools", {})
        
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            
            # Migrate disabled tools
            for server_name, tools in disabled_tools.items():
                for tool_name in tools:
                    cursor.execute("""
                        INSERT OR REPLACE INTO mcp_tool_settings 
                        (server_name, tool_name, enabled, updated_at)
                        VALUES (?, ?, 0, ?)
                    """, (server_name, tool_name, now))
            
            # Migrate custom metadata
            for server_name, tools in custom_tools.items():
                for tool_name, meta in tools.items():
                    cursor.execute("""
                        INSERT INTO mcp_tool_settings 
                        (server_name, tool_name, enabled, custom_name, custom_description, updated_at)
                        VALUES (?, ?, 1, ?, ?, ?)
                        ON CONFLICT(server_name, tool_name) DO UPDATE SET
                        custom_name = excluded.custom_name,
                        custom_description = excluded.custom_description,
                        updated_at = excluded.updated_at
                    """, (server_name, tool_name, meta.get("name"), meta.get("description"), now))
            
            conn.commit()
            
            # Rename old file to backup
            backup_path = DB_DIR / "tools_config.json.bak"
            json_path.rename(backup_path)
            logger.info(f"Migrated tools_config.json to database, backup at {backup_path}")
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Failed to migrate tools_config.json: {e}")


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


def update_endpoint_status(
    endpoint_id: int,
    status: str,
    error: Optional[str] = None
) -> bool:
    """Update connection status for an endpoint.
    
    Args:
        endpoint_id: The endpoint ID to update
        status: Connection status ('disconnected', 'connecting', 'connected', 'error')
        error: Error message if status is 'error'
        
    Returns:
        True if update succeeded, False otherwise
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        if status == 'connected':
            # Update status and set last_connected_at, clear error
            cursor.execute("""
                UPDATE mcp_endpoints 
                SET connection_status = ?, 
                    last_connected_at = ?,
                    connection_error = NULL,
                    updated_at = ?
                WHERE id = ?
            """, (status, now, now, endpoint_id))
        else:
            # Update status and optionally set error
            cursor.execute("""
                UPDATE mcp_endpoints 
                SET connection_status = ?, 
                    connection_error = ?,
                    updated_at = ?
                WHERE id = ?
            """, (status, error, now, endpoint_id))
        
        conn.commit()
        updated = cursor.rowcount > 0
        if updated:
            logger.debug(f"Endpoint {endpoint_id} status updated to '{status}'")
        return updated
    except Exception as e:
        logger.error(f"Failed to update endpoint status: {e}")
        return False
    finally:
        conn.close()


def get_endpoint_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a single endpoint by name.
    
    Args:
        name: The endpoint name
        
    Returns:
        Endpoint dictionary or None if not found
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mcp_endpoints WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# =============================================================================
# Tool Settings CRUD Operations
# =============================================================================

def get_disabled_tools() -> Dict[str, List[str]]:
    """Get all disabled tools grouped by server.
    
    Returns:
        Dictionary mapping server_name -> list of disabled tool names
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT server_name, tool_name 
            FROM mcp_tool_settings 
            WHERE enabled = 0
        """)
        
        result: Dict[str, List[str]] = {}
        for row in cursor.fetchall():
            server_name = row["server_name"]
            tool_name = row["tool_name"]
            if server_name not in result:
                result[server_name] = []
            result[server_name].append(tool_name)
        
        return result
    finally:
        conn.close()


def get_custom_tools() -> Dict[str, Dict[str, Dict[str, str]]]:
    """Get all custom tool metadata grouped by server.
    
    Returns:
        Dictionary mapping server_name -> {tool_name -> {name, description}}
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT server_name, tool_name, custom_name, custom_description 
            FROM mcp_tool_settings 
            WHERE custom_name IS NOT NULL OR custom_description IS NOT NULL
        """)
        
        result: Dict[str, Dict[str, Dict[str, str]]] = {}
        for row in cursor.fetchall():
            server_name = row["server_name"]
            tool_name = row["tool_name"]
            
            if server_name not in result:
                result[server_name] = {}
            
            meta = {}
            if row["custom_name"]:
                meta["name"] = row["custom_name"]
            if row["custom_description"]:
                meta["description"] = row["custom_description"]
            
            if meta:
                result[server_name][tool_name] = meta
        
        return result
    finally:
        conn.close()


def set_tool_enabled(server_name: str, tool_name: str, enabled: bool) -> bool:
    """Enable or disable a tool.
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool
        enabled: Whether the tool should be enabled
        
    Returns:
        True if operation succeeded
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            INSERT INTO mcp_tool_settings (server_name, tool_name, enabled, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(server_name, tool_name) DO UPDATE SET
            enabled = excluded.enabled,
            updated_at = excluded.updated_at
        """, (server_name, tool_name, 1 if enabled else 0, now))
        
        conn.commit()
        logger.info(f"Tool '{tool_name}' from '{server_name}' {'enabled' if enabled else 'disabled'}")
        return True
    except Exception as e:
        logger.error(f"Failed to set tool enabled: {e}")
        return False
    finally:
        conn.close()


def set_tool_custom_metadata(
    server_name: str, 
    tool_name: str, 
    custom_name: Optional[str] = None, 
    custom_description: Optional[str] = None
) -> bool:
    """Set custom metadata for a tool.
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool
        custom_name: Custom display name (optional)
        custom_description: Custom description (optional)
        
    Returns:
        True if operation succeeded
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            INSERT INTO mcp_tool_settings (server_name, tool_name, custom_name, custom_description, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(server_name, tool_name) DO UPDATE SET
            custom_name = COALESCE(excluded.custom_name, custom_name),
            custom_description = COALESCE(excluded.custom_description, custom_description),
            updated_at = excluded.updated_at
        """, (server_name, tool_name, custom_name, custom_description, now))
        
        conn.commit()
        logger.info(f"Updated custom metadata for tool '{tool_name}' from '{server_name}'")
        return True
    except Exception as e:
        logger.error(f"Failed to set tool custom metadata: {e}")
        return False
    finally:
        conn.close()


def reset_tool_metadata(server_name: str, tool_name: str) -> bool:
    """Reset custom metadata for a tool (remove custom name and description).
    
    Args:
        server_name: Name of the MCP server
        tool_name: Name of the tool
        
    Returns:
        True if operation succeeded
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            UPDATE mcp_tool_settings 
            SET custom_name = NULL, custom_description = NULL, updated_at = ?
            WHERE server_name = ? AND tool_name = ?
        """, (now, server_name, tool_name))
        
        conn.commit()
        logger.info(f"Reset metadata for tool '{tool_name}' from '{server_name}'")
        return True
    except Exception as e:
        logger.error(f"Failed to reset tool metadata: {e}")
        return False
    finally:
        conn.close()


def remove_tools_by_server(server_name: str) -> bool:
    """Remove all tool settings for a server (when server is deleted).
    
    Args:
        server_name: Name of the MCP server
        
    Returns:
        True if operation succeeded
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM mcp_tool_settings WHERE server_name = ?
        """, (server_name,))
        
        conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info(f"Removed {deleted} tool settings for server '{server_name}'")
        return True
    except Exception as e:
        logger.error(f"Failed to remove tools by server: {e}")
        return False
    finally:
        conn.close()


def get_all_tool_settings_for_backup() -> Dict[str, Any]:
    """Get all tool settings for backup in the original JSON format.
    
    Returns:
        Dictionary with disabledTools and customTools in original format
    """
    return {
        "disabledTools": get_disabled_tools(),
        "customTools": get_custom_tools()
    }


def restore_tool_settings(disabled_tools: Dict[str, List[str]], custom_tools: Dict[str, Dict[str, Dict[str, str]]]) -> bool:
    """Restore tool settings from backup.
    
    Args:
        disabled_tools: Dictionary mapping server_name -> list of disabled tool names
        custom_tools: Dictionary mapping server_name -> {tool_name -> {name, description}}
        
    Returns:
        True if operation succeeded
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        # Clear existing settings
        cursor.execute("DELETE FROM mcp_tool_settings")
        
        # Restore disabled tools
        for server_name, tools in disabled_tools.items():
            for tool_name in tools:
                cursor.execute("""
                    INSERT INTO mcp_tool_settings 
                    (server_name, tool_name, enabled, updated_at)
                    VALUES (?, ?, 0, ?)
                """, (server_name, tool_name, now))
        
        # Restore custom metadata
        for server_name, tools in custom_tools.items():
            for tool_name, meta in tools.items():
                cursor.execute("""
                    INSERT INTO mcp_tool_settings 
                    (server_name, tool_name, enabled, custom_name, custom_description, updated_at)
                    VALUES (?, ?, 1, ?, ?, ?)
                    ON CONFLICT(server_name, tool_name) DO UPDATE SET
                    custom_name = excluded.custom_name,
                    custom_description = excluded.custom_description,
                    updated_at = excluded.updated_at
                """, (server_name, tool_name, meta.get("name"), meta.get("description"), now))
        
        conn.commit()
        logger.info("Restored tool settings from backup")
        return True
    except Exception as e:
        logger.error(f"Failed to restore tool settings: {e}")
        return False
    finally:
        conn.close()
