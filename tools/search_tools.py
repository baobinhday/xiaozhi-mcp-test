"""Search tool functions."""
import sys
from ddgs import DDGS
from typing import Dict, Any

# --- UTF-8 ENCODING FIX FOR WINDOWS ---
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Initialize web search tool
ddgs = DDGS()


def tim_kiem_web(truy_van: str, so_ket_qua: int = 5) -> Dict[str, Any]:
    """
    Tìm kiếm thông tin trên web bằng DuckDuckGo.
    
    Args:
        truy_van (str): Nội dung cần tìm kiếm.
        so_ket_qua (int): Số lượng kết quả tối đa muốn trả về (mặc định là 5).
    """
    print(f"[Tool] Đang thực thi 'tim_kiem_web' với truy vấn: {truy_van}")
    try:
        results = ddgs.text(
            truy_van,
            region="vi-vn",
            safesearch="off",
            max_results=so_ket_qua
        )
        
        if not results:
            return {"success": True, "results": "Không tìm thấy kết quả nào."}
        
        formatted_results = [
            {
                "title": r.get("title"),
                "url": r.get("href"),
                "snippet": r.get("body")
            } for r in results
        ]
        return {"success": True, "results": formatted_results}
    except Exception as e:
        print(f"[Tool Error] Lỗi khi tìm kiếm: {e}")
        return {"success": False, "error": str(e)}
<<<<<<< HEAD
=======


def doc_tin_tuc_moi_nhat(so_bai_bao_toi_da: int = 3) -> Dict[str, Any]:
    """
    Lấy các tin tức mới nhất từ các trang báo hàng đầu Việt Nam qua RSS.
    
    Args:
        so_bai_bao_toi_da (int): Số lượng bài báo tối đa lấy từ mỗi nguồn.
    """
    print(f"[Tool] Đang thực thi 'doc_tin_tuc_moi_nhat'")
    RSS_FEEDS = {
        "VnExpress": "https://vnexpress.net/rss/tin-moi-nhat.rss",
        "Tuoi Tre": "https://tuoitre.vn/rss/tin-moi-nhat.rss",
        "Thanh Nien": "https://thanhnien.vn/rss/home.rss"
    }
    all_news = {}
    try:
        for source_name, url in RSS_FEEDS.items():
            feed = feedparser.parse(url)
            articles_list = []
            for entry in feed.entries[:so_bai_bao_toi_da]:
                articles_list.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get("summary", "N/A"),
                })
            all_news[source_name] = articles_list
        return {"success": True, "news": all_news}
    except Exception as e:
        print(f"[Tool Error] Lỗi khi đọc RSS: {e}")
        return {"success": False, "error": str(e)}
>>>>>>> main
