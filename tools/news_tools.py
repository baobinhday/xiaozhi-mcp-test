"""News tool functions for fetching RSS feeds."""

import logging
from typing import Any, Dict, List

import feedparser

logger = logging.getLogger("news_tools")

# RSS feeds by category (VNExpress)
RSS_FEEDS_BY_CATEGORY: Dict[str, str] = {
    "tin-moi": "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "thoi-su": "https://vnexpress.net/rss/thoi-su.rss",
    "the-gioi": "https://vnexpress.net/rss/the-gioi.rss",
    "kinh-doanh": "https://vnexpress.net/rss/kinh-doanh.rss",
    "startup": "https://vnexpress.net/rss/startup.rss",
    "giai-tri": "https://vnexpress.net/rss/giai-tri.rss",
    "the-thao": "https://vnexpress.net/rss/the-thao.rss",
    "phap-luat": "https://vnexpress.net/rss/phap-luat.rss",
    "giao-duc": "https://vnexpress.net/rss/giao-duc.rss",
    "suc-khoe": "https://vnexpress.net/rss/suc-khoe.rss",
    "doi-song": "https://vnexpress.net/rss/doi-song.rss",
    "du-lich": "https://vnexpress.net/rss/du-lich.rss",
    "khoa-hoc_cong-nghe": "https://vnexpress.net/rss/khoa-hoc.rss",
    "oto-xe-may": "https://vnexpress.net/rss/oto-xe-may.rss",
}

# Available topics for documentation
AVAILABLE_TOPICS = list(RSS_FEEDS_BY_CATEGORY.keys())


def get_latest_news(topic: str = "tin-moi", limit: int = 5) -> Dict[str, Any]:
    """Get latest news from VNExpress by topic.

    Fetches the latest news articles from VNExpress RSS feeds based on
    the specified topic category.

    Args:
        topic: News category to fetch. Available options:
            tin-moi, the-gioi, thoi-su, the-thao, khoa-hoc_cong-nghe,
            giai-tri, kinh-doanh, suc-khoe, du-lich, startup,
            phap-luat, giao-duc, doi-song, oto-xe-may.
            Defaults to "tin-moi" (latest news).
        limit: Maximum number of articles to return (default: 5).

    Returns:
        Dict with 'success' status and 'news' list or 'error' message.
        Each news item contains 'title', 'link', and 'summary'.

    Examples:
        >>> get_latest_news("the-thao", limit=3)
        {'success': True, 'news': [...]}
    """
    # Get RSS URL, fallback to "tin-moi" if topic not found
    url = RSS_FEEDS_BY_CATEGORY.get(topic, RSS_FEEDS_BY_CATEGORY["tin-moi"])

    try:
        feed = feedparser.parse(url)

        articles: List[Dict[str, str]] = []
        for entry in feed.entries[:limit]:
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", "N/A"),
            })

        logger.info(f"Fetched {len(articles)} articles for topic: {topic}")
        return {"success": True, "news": articles}

    except Exception as e:
        logger.error(f"Error fetching RSS feed: {e}")
        return {"success": False, "error": str(e)}
