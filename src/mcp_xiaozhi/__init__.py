"""MCP Xiaozhi - WebSocket-stdio bridge with agent tools.

This package provides a bridge between MCP servers and WebSocket endpoints,
enabling communication between local Python-based agent tools and remote systems.
"""

__version__ = "0.3.0"

from .main import main

__all__ = ["main", "__version__"]
