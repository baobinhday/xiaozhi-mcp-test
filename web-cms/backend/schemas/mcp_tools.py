"""MCP Tools schemas for tool management."""

from typing import Optional

from pydantic import BaseModel


class ToolToggle(BaseModel):
    serverName: str
    toolName: str
    enabled: bool


class ToolUpdate(BaseModel):
    serverName: str
    toolName: str
    customName: Optional[str] = None
    customDescription: Optional[str] = None


class ToolReset(BaseModel):
    serverName: str
    toolName: str


class ToolRefresh(BaseModel):
    serverName: Optional[str] = None
