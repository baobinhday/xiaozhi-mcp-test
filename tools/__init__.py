"""Tools package for MCP Xiaozhi.

This package provides various tools that can be exposed through MCP servers:
- calculator: Mathematical expression evaluation
- web_search: DuckDuckGo web search
- get_latest_news: VNExpress RSS news fetching
"""

from tools.math_tools import calculator
from tools.news_tools import get_latest_news
from tools.search_tools import tim_kiem_web, web_search

__all__ = [
    "calculator",
    "get_latest_news",
    "web_search",
    "tim_kiem_web",  # Backward compatibility
]
