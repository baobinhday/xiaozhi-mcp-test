"""Search tool functions."""

import logging
from typing import Any, Dict, List, Optional

from ddgs import DDGS

logger = logging.getLogger("search_tools")

# Initialize web search client
_ddgs = DDGS()


def web_search(
    query: str,
    max_results: int = 5,
    region: str = "vi-vn",
) -> Dict[str, Any]:
    """Search the web using DuckDuckGo.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (default: 5).
        region: Region code for search results (default: "vi-vn" for Vietnam).

    Returns:
        Dict with 'success' status and 'results' list or 'error' message.
        Each result contains 'title', 'url', and 'snippet'.

    Examples:
        >>> web_search("Python best practices")
        {'success': True, 'results': [...]}
    """
    logger.info(f"Executing web search with query: {query}")

    try:
        results = _ddgs.text(
            query,
            region=region,
            safesearch="on",
            max_results=max_results,
        )

        if not results:
            return {"success": True, "results": "No results found."}

        formatted_results: List[Dict[str, Optional[str]]] = [
            {
                "title": r.get("title"),
                "url": r.get("href"),
                "snippet": r.get("body"),
            }
            for r in results
        ]

        return {"success": True, "results": formatted_results}

    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"success": False, "error": str(e)}


# Alias for backward compatibility
tim_kiem_web = web_search
