"""MCP Server schemas for CRUD operations."""

from typing import Optional

from pydantic import BaseModel


class MCPServerCreate(BaseModel):
    name: str
    type: str = "stdio"
    command: Optional[str] = None
    args: Optional[list] = None
    env: Optional[dict] = None
    url: Optional[str] = None
    headers: Optional[dict] = None
    disabled: Optional[bool] = None


class MCPServerUpdate(BaseModel):
    type: Optional[str] = None
    command: Optional[str] = None
    args: Optional[list] = None
    env: Optional[dict] = None
    url: Optional[str] = None
    headers: Optional[dict] = None
    disabled: Optional[bool] = None
