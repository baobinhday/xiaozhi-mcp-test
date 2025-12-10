"""Utility functions for tools module."""

from bs4 import NavigableString


def get_text_from_tag(tag) -> str:
    """Extract text content from a BeautifulSoup tag or NavigableString.

    Args:
        tag: A BeautifulSoup Tag or NavigableString element.

    Returns:
        The text content of the tag as a stripped string,
        or empty string if tag is None or extraction fails.
    """
    if tag is None:
        return ""
    if isinstance(tag, NavigableString):
        return str(tag).strip()
    return tag.get_text(strip=True) if hasattr(tag, "get_text") else ""
