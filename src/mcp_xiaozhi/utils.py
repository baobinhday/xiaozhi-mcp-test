"""Shared utilities for MCP Xiaozhi."""

import io
import logging
import sys
from typing import Optional


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    pass


class ConfigurationError(MCPError):
    """Configuration-related errors."""

    pass


class ConnectionError(MCPError):
    """Connection-related errors."""

    pass


def setup_logging(
    name: str = "MCP_PIPE",
    level: int = logging.INFO,
    fmt: Optional[str] = None,
) -> logging.Logger:
    """Configure and return a logger instance.

    Args:
        name: Logger name
        level: Logging level
        fmt: Optional format string

    Returns:
        Configured logger instance
    """
    if fmt is None:
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(level=level, format=fmt)
    return logging.getLogger(name)


def fix_windows_encoding() -> None:
    """Fix UTF-8 encoding issues on Windows.

    Wraps stdout and stderr with UTF-8 encoding on Windows systems
    to prevent encoding errors with non-ASCII characters.
    """
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )
