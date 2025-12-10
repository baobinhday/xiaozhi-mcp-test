"""Tools package for MCP Xiaozhi.

This package provides various tools that can be exposed through MCP servers:
- calculator: Mathematical expression evaluation
- web_search: DuckDuckGo web search
- get_latest_news: VNExpress RSS news fetching
- gold_tools: Gold price fetching (SJC, DOJI, PNJ)
"""

from tools.gold_tools import (
    get_all_gold_prices,
    get_doji_gold_price,
    get_pnj_gold_price,
    get_sjc_gold_price,
)
from tools.math_tools import calculator
from tools.news_tools import (
    get_detail_news_content_from_dantri,
    get_detail_news_content_from_vnexpress,
    get_latest_news_from_dantri,
    get_latest_news_from_vnexpress,
)
from tools.search_tools import tim_kiem_web, web_search

__all__ = [
    "calculator",
    "get_all_gold_prices",
    "get_doji_gold_price",
    "get_latest_news_from_dantri",
    "get_latest_news_from_vnexpress",
    "get_detail_news_content_from_dantri",
    "get_detail_news_content_from_vnexpress",
    "get_pnj_gold_price",
    "get_sjc_gold_price",
    "web_search",
    "tim_kiem_web",  # Backward compatibility
]
