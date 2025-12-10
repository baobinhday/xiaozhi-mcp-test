"""News tool functions for fetching RSS feeds."""

import logging
from typing import Any, Dict, List

import feedparser
from bs4 import BeautifulSoup
import requests

from tools.utils import get_text_from_tag

logger = logging.getLogger("news_tools")

# RSS feeds by category (VNExpress)
RSS_FEEDS_BY_CATEGORY_VNEXPRESS: Dict[str, str] = {
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
AVAILABLE_TOPICS = list(RSS_FEEDS_BY_CATEGORY_VNEXPRESS.keys())


def get_latest_news_from_vnexpress(topic: str = "tin-moi", limit: int = 5) -> Dict[str, Any]:
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
    url = RSS_FEEDS_BY_CATEGORY_VNEXPRESS.get(topic, RSS_FEEDS_BY_CATEGORY_VNEXPRESS["tin-moi"])

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


def get_detail_news_content_from_vnexpress(url: str, timeout: int = 10) -> tuple[str | None, List[str] | None, List[str] | None]:
    """Get detail of news from VNExpress URL.

    Fetches the detail content of news from VNExpress URL

    Args:
        url: The VNExpress article URL to fetch content from.
        timeout: Request timeout in seconds (default: 10).

    Returns:
        A tuple of (title, description, paragraphs):
        - title: Article title string, or None if not found.
        - description: List of description text segments, or None if not found.
        - paragraphs: List of paragraph texts, or None if not found.

    Examples:
        >>> title, desc, paragraphs = get_detail_news_content("https://vnexpress.net/...")
        >>> if title:
        ...     print(f"Title: {title}")
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        return None, None, None

    soup = BeautifulSoup(response.content, "html.parser")

    title_tag = soup.find("h1", class_="title-detail")
    if title_tag is None:
        logger.warning(f"No title found for URL: {url}")
        return None, None, None
    
    title = title_tag.get_text(strip=True)

    # Extract description - some sport news have location-stamp child tag inside description tag
    description_tag = soup.find("p", class_="description")
    description: List[str] | None = None
    if description_tag:
        description = [
            text for text in 
            (get_text_from_tag(p) for p in description_tag.contents)
            if text  # Filter out empty strings
        ]

    # Extract body paragraphs
    paragraph_tags = soup.find_all("p", class_="Normal")
    paragraphs: List[str] | None = None
    if paragraph_tags:
        paragraphs = [
            text for text in
            (get_text_from_tag(p) for p in paragraph_tags)
            if text  # Filter out empty strings
        ]

    return title, description, paragraphs


# RSS feeds by category (Dan tri)
RSS_FEEDS_BY_CATEGORY_DANTRI: Dict[str, str] = {
    "tin-moi-nhat": "https://dantri.com.vn/rss/home.rss",
    "su-kien": "https://dantri.com.vn/rss/su-kien.rss",
    "thoi-su": "https://dantri.com.vn/rss/thoi-su.rss",
    "the-gioi": "https://dantri.com.vn/rss/the-gioi.rss",
    "gia-vang": "https://dantri.com.vn/rss/gia-vang.rss",
    "doi-song": "https://dantri.com.vn/rss/doi-song.rss",
    "the-thao": "https://dantri.com.vn/rss/the-thao.rss",
    "lao-dong-viec-lam": "https://dantri.com.vn/rss/lao-dong-viec-lam.rss",
    "giao-duc": "https://dantri.com.vn/rss/giao-duc.rss",
    "kinh-doanh": "https://dantri.com.vn/rss/kinh-doanh.rss",
    "bat-dong-san": "https://dantri.com.vn/rss/bat-dong-san.rss",
    "giai-tri": "https://dantri.com.vn/rss/giai-tri.rss",
    "du-lich": "https://dantri.com.vn/rss/du-lich.rss",
    "phap-luat": "https://dantri.com.vn/rss/phap-luat.rss",
    "suc-khoe": "https://dantri.com.vn/rss/suc-khoe.rss",
    "cong-nghe": "https://dantri.com.vn/rss/cong-nghe.rss",
    "o-to-xe-may": "https://dantri.com.vn/rss/o-to-xe-may.rss",
    "khoa-hoc": "https://dantri.com.vn/rss/khoa-hoc.rss",
    "noi-vu": "https://dantri.com.vn/rss/noi-vu.rss",
    "tam-diem": "https://dantri.com.vn/rss/tam-diem.rss",
}


def get_latest_news_from_dantri(topic: str = "tin-moi-nhat", limit: int = 5) -> Dict[str, Any]:
    """Get latest news from Dantri by topic.

    Fetches the latest news articles from Dantri RSS feeds based on
    the specified topic category.

    Args:
        topic: News category to fetch. Available options:
            tin-moi-nhat, su-kien, thoi-su, the-gioi, gia-vang, doi-song,
            the-thao, lao-dong-viec-lam, giao-duc, kinh-doanh, bat-dong-san,
            giai-tri, du-lich, phap-luat, suc-khoe, cong-nghe, o-to-xe-may,
            khoa-hoc, noi-vu, tam-diem.
            Defaults to "tin-moi-nhat" (latest news).
        limit: Maximum number of articles to return (default: 5).

    Returns:
        Dict with 'success' status and 'news' list or 'error' message.
        Each news item contains 'title', 'link', and 'summary'.

    Examples:
        >>> get_latest_news_from_dantri("the-thao", limit=3)
        {'success': True, 'news': [...]}
    """
    # Get RSS URL, fallback to "tin-moi-nhat" if topic not found
    url = RSS_FEEDS_BY_CATEGORY_DANTRI.get(topic, RSS_FEEDS_BY_CATEGORY_DANTRI["tin-moi-nhat"])

    try:
        feed = feedparser.parse(url)

        articles: List[Dict[str, str]] = []
        for entry in feed.entries[:limit]:
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", "N/A"),
            })

        logger.info(f"Fetched {len(articles)} articles from Dantri for topic: {topic}")
        return {"success": True, "news": articles}

    except Exception as e:
        logger.error(f"Error fetching Dantri RSS feed: {e}")
        return {"success": False, "error": str(e)}


def get_detail_news_content_from_dantri(url: str, timeout: int = 10) -> tuple[str | None, List[str] | None, List[str] | None]:
    """Get detail of news from Dan tri URL.

    Fetches the detail content of news from Dan tri URL

    Args:
        url: The Dantri article URL to fetch content from.
        timeout: Request timeout in seconds (default: 10).

    Returns:
        A tuple of (title, description, paragraphs):
        - title: Article title string, or None if not found.
        - description: List of description text segments, or None if not found.
        - paragraphs: List of paragraph texts, or None if not found.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        return None, None, None

    soup = BeautifulSoup(response.content, "html.parser")

    title_tag = soup.find("h1", class_="title-page detail")
    if title_tag is None:
        logger.warning(f"No title found for URL: {url}")
        return None, None, None
    title = title_tag.get_text(strip=True)

    description_tag = soup.find("h2", class_="singular-sapo")
    description: List[str] | None = None
    if description_tag:
        description = [
            text for text in 
            (get_text_from_tag(p) for p in description_tag.contents)
            if text
        ]

    content_div = soup.find("div", class_="singular-content")
    paragraphs: List[str] | None = None
    if content_div:
        paragraph_tags = content_div.find_all("p")
        if paragraph_tags:
            paragraphs = [
                 text for text in
                 (get_text_from_tag(p) for p in paragraph_tags)
                 if text
            ]

    return title, description, paragraphs
