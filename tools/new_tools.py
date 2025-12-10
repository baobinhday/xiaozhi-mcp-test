"""News tool functions."""
import sys
import feedparser
from typing import Dict, Any

# --- UTF-8 ENCODING FIX FOR WINDOWS ---
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# def doc_tin_tuc_moi_nhat(so_bai_bao_toi_da: int = 3) -> Dict[str, Any]:
#     """
#     Lấy các tin tức mới nhất từ các trang báo hàng đầu Việt Nam qua RSS.
    
#     Args:
#         so_bai_bao_toi_da (int): Số lượng bài báo tối đa lấy từ mỗi nguồn.
#     """
#     print(f"[Tool] Đang thực thi 'doc_tin_tuc_moi_nhat'")
#     RSS_FEEDS = {
#         "VnExpress": "https://vnexpress.net/rss/tin-moi-nhat.rss",
#         "Tuoi Tre": "https://tuoitre.vn/rss/tin-moi-nhat.rss",
#         "Thanh Nien": "https://thanhnien.vn/rss/home.rss"
#     }
#     all_news = {}
#     try:
#         for source_name, url in RSS_FEEDS.items():
#             feed = feedparser.parse(url)
#             articles_list = []
#             for entry in feed.entries[:so_bai_bao_toi_da]:
#                 articles_list.append({
#                     "title": entry.title,
#                     "link": entry.link,
#                     "summary": entry.get("summary", "N/A"),
#                 })
#             all_news[source_name] = articles_list
#         return {"success": True, "news": all_news}
#     except Exception as e:
#         print(f"[Tool Error] Lỗi khi đọc RSS: {e}")
#         return {"success": False, "error": str(e)}

# === Nguồn RSS theo chủ đề ===
RSS_FEEDS_BY_CATEGORY = {
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

def get_latest_news(topic: str = "tin-moi", limit: int = 5) -> Dict[str,Any]:
    """
    Lấy tin tức mới nhất từ VNExpress theo chủ đề.
    Chủ đề hỗ trợ: tin-moi, the-gioi, thoi-su, the-thao, khoa-hoc_cong-nghe, giai-tri, kinh-doanh, suc-khoe, du-lich, startup, phap-luat, giao-duc, doi-song, oto-xe-may
    """
    url = RSS_FEEDS_BY_CATEGORY.get(topic, RSS_FEEDS_BY_CATEGORY["tin-moi"])
    try:
        feed = feedparser.parse(url)
        articles_list = []
        for entry in feed.entries[:limit]:
            articles_list.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", "N/A"),
            })
        return {"success": True, "news": articles_list}
    except Exception as e:
        print(f"[Tool Error] Lỗi khi đọc RSS: {e}")
        return {"success": False, "error": str(e)}
