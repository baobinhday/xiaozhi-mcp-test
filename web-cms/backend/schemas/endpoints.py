"""Endpoint schemas for CRUD operations."""

from typing import Optional

from pydantic import BaseModel


class EndpointCreate(BaseModel):
    name: str
    url: str
    enabled: bool = True


class EndpointUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    enabled: Optional[int] = None
