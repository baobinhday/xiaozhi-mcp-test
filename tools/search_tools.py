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
