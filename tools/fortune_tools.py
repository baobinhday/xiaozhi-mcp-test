"""Fortune telling (Xem bói) tool functions.

Provides various Vietnamese and international fortune telling methods:
- Zodiac signs (Western & Vietnamese)
- Five Elements (Ngũ Hành)
- I Ching (Kinh Dịch)
- Daily horoscope
- Lucky numbers
- Marriage compatibility
"""

import logging
import random
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger("fortune_tools")

# ===============================
# ZODIAC DATA (Cung Hoàng Đạo)
# ===============================

ZODIAC_SIGNS = {
    "bach_duong": {
        "name": "Bạch Dương",
        "english": "Aries",
        "symbol": "♈",
        "element": "Hỏa",
        "dates": "21/3 - 19/4",
        "traits": ["Nhiệt huyết", "Dũng cảm", "Quyết đoán", "Thích phiêu lưu"],
        "compatible": ["sư_tử", "nhân_mã", "song_tử", "bảo_bình"],
        "lucky_colors": ["Đỏ", "Cam"],
        "lucky_numbers": [1, 9],
    },
    "kim_nguu": {
        "name": "Kim Ngưu",
        "english": "Taurus",
        "symbol": "♉",
        "element": "Thổ",
        "dates": "20/4 - 20/5",
        "traits": ["Kiên nhẫn", "Đáng tin cậy", "Thực tế", "Quyết tâm"],
        "compatible": ["xử_nữ", "ma_kết", "cự_giải", "song_ngư"],
        "lucky_colors": ["Xanh lá", "Hồng"],
        "lucky_numbers": [2, 6],
    },
    "song_tu": {
        "name": "Song Tử",
        "english": "Gemini",
        "symbol": "♊",
        "element": "Khí",
        "dates": "21/5 - 20/6",
        "traits": ["Linh hoạt", "Thông minh", "Hòa đồng", "Tò mò"],
        "compatible": ["thiên_bình", "bảo_bình", "bạch_dương", "sư_tử"],
        "lucky_colors": ["Vàng", "Xanh dương nhạt"],
        "lucky_numbers": [3, 5],
    },
    "cu_giai": {
        "name": "Cự Giải",
        "english": "Cancer",
        "symbol": "♋",
        "element": "Thủy",
        "dates": "21/6 - 22/7",
        "traits": ["Trực giác", "Tình cảm", "Thương người", "Kiên trì"],
        "compatible": ["bọ_cạp", "song_ngư", "kim_ngưu", "xử_nữ"],
        "lucky_colors": ["Trắng", "Bạc"],
        "lucky_numbers": [2, 7],
    },
    "su_tu": {
        "name": "Sư Tử",
        "english": "Leo",
        "symbol": "♌",
        "element": "Hỏa",
        "dates": "23/7 - 22/8",
        "traits": ["Sáng tạo", "Nhiệt tình", "Hào phóng", "Vui vẻ"],
        "compatible": ["bạch_dương", "nhân_mã", "song_tử", "thiên_bình"],
        "lucky_colors": ["Vàng gold", "Cam"],
        "lucky_numbers": [1, 4],
    },
    "xu_nu": {
        "name": "Xử Nữ",
        "english": "Virgo",
        "symbol": "♍",
        "element": "Thổ",
        "dates": "23/8 - 22/9",
        "traits": ["Tỉ mỉ", "Phân tích", "Siêng năng", "Thực tế"],
        "compatible": ["kim_ngưu", "ma_kết", "cự_giải", "bọ_cạp"],
        "lucky_colors": ["Xanh navy", "Xám"],
        "lucky_numbers": [5, 6],
    },
    "thien_binh": {
        "name": "Thiên Bình",
        "english": "Libra",
        "symbol": "♎",
        "element": "Khí",
        "dates": "23/9 - 22/10",
        "traits": ["Công bằng", "Lịch sự", "Hòa nhã", "Xã giao"],
        "compatible": ["song_tử", "bảo_bình", "sư_tử", "nhân_mã"],
        "lucky_colors": ["Hồng", "Xanh lá nhạt"],
        "lucky_numbers": [6, 9],
    },
    "bo_cap": {
        "name": "Bọ Cạp",
        "english": "Scorpio",
        "symbol": "♏",
        "element": "Thủy",
        "dates": "23/10 - 21/11",
        "traits": ["Quyết tâm", "Dũng cảm", "Tận tụy", "Bí ẩn"],
        "compatible": ["cự_giải", "song_ngư", "xử_nữ", "ma_kết"],
        "lucky_colors": ["Đỏ đậm", "Đen"],
        "lucky_numbers": [8, 11],
    },
    "nhan_ma": {
        "name": "Nhân Mã",
        "english": "Sagittarius",
        "symbol": "♐",
        "element": "Hỏa",
        "dates": "22/11 - 21/12",
        "traits": ["Lạc quan", "Yêu tự do", "Hài hước", "Thẳng thắn"],
        "compatible": ["bạch_dương", "sư_tử", "thiên_bình", "bảo_bình"],
        "lucky_colors": ["Tím", "Xanh dương"],
        "lucky_numbers": [3, 9],
    },
    "ma_ket": {
        "name": "Ma Kết",
        "english": "Capricorn",
        "symbol": "♑",
        "element": "Thổ",
        "dates": "22/12 - 19/1",
        "traits": ["Kỷ luật", "Có trách nhiệm", "Tự chủ", "Tham vọng"],
        "compatible": ["kim_ngưu", "xử_nữ", "bọ_cạp", "song_ngư"],
        "lucky_colors": ["Nâu", "Đen"],
        "lucky_numbers": [4, 8],
    },
    "bao_binh": {
        "name": "Bảo Bình",
        "english": "Aquarius",
        "symbol": "♒",
        "element": "Khí",
        "dates": "20/1 - 18/2",
        "traits": ["Tiến bộ", "Độc lập", "Nhân đạo", "Sáng tạo"],
        "compatible": ["song_tử", "thiên_bình", "bạch_dương", "nhân_mã"],
        "lucky_colors": ["Xanh dương", "Bạc"],
        "lucky_numbers": [4, 7],
    },
    "song_ngu": {
        "name": "Song Ngư",
        "english": "Pisces",
        "symbol": "♓",
        "element": "Thủy",
        "dates": "19/2 - 20/3",
        "traits": ["Trực giác", "Nghệ sĩ", "Nhạy cảm", "Thông cảm"],
        "compatible": ["cự_giải", "bọ_cạp", "kim_ngưu", "ma_kết"],
        "lucky_colors": ["Xanh ngọc", "Tím nhạt"],
        "lucky_numbers": [3, 7],
    },
}

# ===============================
# VIETNAMESE ZODIAC (Con giáp)
# ===============================

CON_GIAP = {
    0: {"name": "Thân", "animal": "Khỉ", "traits": ["Thông minh", "Linh hoạt", "Tò mò", "Hòa đồng"]},
    1: {"name": "Dậu", "animal": "Gà", "traits": ["Chăm chỉ", "Tự tin", "Năng động", "Thực tế"]},
    2: {"name": "Tuất", "animal": "Chó", "traits": ["Trung thành", "Thật thà", "Thận trọng", "Tận tụy"]},
    3: {"name": "Hợi", "animal": "Lợn", "traits": ["Tốt bụng", "Kiên nhẫn", "Chân thành", "Rộng lượng"]},
    4: {"name": "Tý", "animal": "Chuột", "traits": ["Thông minh", "Nhanh nhẹn", "Tiết kiệm", "Cẩn thận"]},
    5: {"name": "Sửu", "animal": "Trâu", "traits": ["Siêng năng", "Đáng tin", "Kiên nhẫn", "Cần cù"]},
    6: {"name": "Dần", "animal": "Hổ", "traits": ["Dũng cảm", "Tự tin", "Nhiệt huyết", "Mạnh mẽ"]},
    7: {"name": "Mão", "animal": "Mèo", "traits": ["Nhạy cảm", "Tinh tế", "Khéo léo", "Điềm tĩnh"]},
    8: {"name": "Thìn", "animal": "Rồng", "traits": ["Năng động", "May mắn", "Quyền uy", "Cao quý"]},
    9: {"name": "Tỵ", "animal": "Rắn", "traits": ["Khôn ngoan", "Bí ẩn", "Quyến rũ", "Sâu sắc"]},
    10: {"name": "Ngọ", "animal": "Ngựa", "traits": ["Tự do", "Hoạt bát", "Năng động", "Nhiệt tình"]},
    11: {"name": "Mùi", "animal": "Dê", "traits": ["Hiền lành", "Nghệ sĩ", "Nhạy cảm", "Hòa nhã"]},
}

# ===============================
# FIVE ELEMENTS (Ngũ Hành)
# ===============================

NGU_HANH_MENH = {
    # Giáp Tý, Ất Sửu (1924, 1925, 1984, 1985)
    (1924, 1984): "Hải Trung Kim",
    (1925, 1985): "Hải Trung Kim",
    # Bính Dần, Đinh Mão (1926, 1927, 1986, 1987)
    (1926, 1986): "Lô Trung Hỏa",
    (1927, 1987): "Lô Trung Hỏa",
    # Mậu Thìn, Kỷ Tỵ (1928, 1929, 1988, 1989)
    (1928, 1988): "Đại Lâm Mộc",
    (1929, 1989): "Đại Lâm Mộc",
    # Canh Ngọ, Tân Mùi (1930, 1931, 1990, 1991)
    (1930, 1990): "Lộ Bàng Thổ",
    (1931, 1991): "Lộ Bàng Thổ",
    # Nhâm Thân, Quý Dậu (1932, 1933, 1992, 1993)
    (1932, 1992): "Kiếm Phong Kim",
    (1933, 1993): "Kiếm Phong Kim",
    # Giáp Tuất, Ất Hợi (1934, 1935, 1994, 1995)
    (1934, 1994): "Sơn Đầu Hỏa",
    (1935, 1995): "Sơn Đầu Hỏa",
    # Bính Tý, Đinh Sửu (1936, 1937, 1996, 1997)
    (1936, 1996): "Giản Hạ Thủy",
    (1937, 1997): "Giản Hạ Thủy",
    # Mậu Dần, Kỷ Mão (1938, 1939, 1998, 1999)
    (1938, 1998): "Thành Đầu Thổ",
    (1939, 1999): "Thành Đầu Thổ",
    # Canh Thìn, Tân Tỵ (1940, 1941, 2000, 2001)
    (1940, 2000): "Bạch Lạp Kim",
    (1941, 2001): "Bạch Lạp Kim",
    # Nhâm Ngọ, Quý Mùi (1942, 1943, 2002, 2003)
    (1942, 2002): "Dương Liễu Mộc",
    (1943, 2003): "Dương Liễu Mộc",
    # Giáp Thân, Ất Dậu (1944, 1945, 2004, 2005)
    (1944, 2004): "Tuyền Trung Thủy",
    (1945, 2005): "Tuyền Trung Thủy",
    # Bính Tuất, Đinh Hợi (1946, 1947, 2006, 2007)
    (1946, 2006): "Ốc Thượng Thổ",
    (1947, 2007): "Ốc Thượng Thổ",
    # Mậu Tý, Kỷ Sửu (1948, 1949, 2008, 2009)
    (1948, 2008): "Tích Lịch Hỏa",
    (1949, 2009): "Tích Lịch Hỏa",
    # Canh Dần, Tân Mão (1950, 1951, 2010, 2011)
    (1950, 2010): "Tùng Bách Mộc",
    (1951, 2011): "Tùng Bách Mộc",
    # Nhâm Thìn, Quý Tỵ (1952, 1953, 2012, 2013)
    (1952, 2012): "Trường Lưu Thủy",
    (1953, 2013): "Trường Lưu Thủy",
    # Giáp Ngọ, Ất Mùi (1954, 1955, 2014, 2015)
    (1954, 2014): "Sa Trung Kim",
    (1955, 2015): "Sa Trung Kim",
    # Bính Thân, Đinh Dậu (1956, 1957, 2016, 2017)
    (1956, 2016): "Sơn Hạ Hỏa",
    (1957, 2017): "Sơn Hạ Hỏa",
    # Mậu Tuất, Kỷ Hợi (1958, 1959, 2018, 2019)
    (1958, 2018): "Bình Địa Mộc",
    (1959, 2019): "Bình Địa Mộc",
    # Canh Tý, Tân Sửu (1960, 1961, 2020, 2021)
    (1960, 2020): "Bích Thượng Thổ",
    (1961, 2021): "Bích Thượng Thổ",
    # Nhâm Dần, Quý Mão (1962, 1963, 2022, 2023)
    (1962, 2022): "Kim Bạc Kim",
    (1963, 2023): "Kim Bạc Kim",
    # Giáp Thìn, Ất Tỵ (1964, 1965, 2024, 2025)
    (1964, 2024): "Phú Đăng Hỏa",
    (1965, 2025): "Phú Đăng Hỏa",
    # Bính Ngọ, Đinh Mùi (1966, 1967)
    (1966,): "Thiên Hà Thủy",
    (1967,): "Thiên Hà Thủy",
    # Mậu Thân, Kỷ Dậu (1968, 1969)
    (1968,): "Đại Trạch Thổ",
    (1969,): "Đại Trạch Thổ",
    # Canh Tuất, Tân Hợi (1970, 1971)
    (1970,): "Thoa Xuyến Kim",
    (1971,): "Thoa Xuyến Kim",
    # Nhâm Tý, Quý Sửu (1972, 1973)
    (1972,): "Tang Đố Mộc",
    (1973,): "Tang Đố Mộc",
    # Giáp Dần, Ất Mão (1974, 1975)
    (1974,): "Đại Khe Thủy",
    (1975,): "Đại Khe Thủy",
    # Bính Thìn, Đinh Tỵ (1976, 1977)
    (1976,): "Sa Trung Thổ",
    (1977,): "Sa Trung Thổ",
    # Mậu Ngọ, Kỷ Mùi (1978, 1979)
    (1978,): "Thiên Thượng Hỏa",
    (1979,): "Thiên Thượng Hỏa",
    # Canh Thân, Tân Dậu (1980, 1981)
    (1980,): "Thạch Lựu Mộc",
    (1981,): "Thạch Lựu Mộc",
    # Nhâm Tuất, Quý Hợi (1982, 1983)
    (1982,): "Đại Hải Thủy",
    (1983,): "Đại Hải Thủy",
}

NGU_HANH_ELEMENT = {
    "Kim": {"color": ["Trắng", "Bạc", "Vàng"], "direction": "Tây", "season": "Thu"},
    "Mộc": {"color": ["Xanh lá", "Xanh lục"], "direction": "Đông", "season": "Xuân"},
    "Thủy": {"color": ["Đen", "Xanh đen", "Xanh dương"], "direction": "Bắc", "season": "Đông"},
    "Hỏa": {"color": ["Đỏ", "Cam", "Hồng"], "direction": "Nam", "season": "Hạ"},
    "Thổ": {"color": ["Vàng", "Nâu", "Be"], "direction": "Trung tâm", "season": "Giao mùa"},
}

# Tương sinh: Kim sinh Thủy, Thủy sinh Mộc, Mộc sinh Hỏa, Hỏa sinh Thổ, Thổ sinh Kim
TUONG_SINH = {"Kim": "Thủy", "Thủy": "Mộc", "Mộc": "Hỏa", "Hỏa": "Thổ", "Thổ": "Kim"}

# Tương khắc: Kim khắc Mộc, Mộc khắc Thổ, Thổ khắc Thủy, Thủy khắc Hỏa, Hỏa khắc Kim
TUONG_KHAC = {"Kim": "Mộc", "Mộc": "Thổ", "Thổ": "Thủy", "Thủy": "Hỏa", "Hỏa": "Kim"}

# ===============================
# I CHING (Kinh Dịch) - 64 Quẻ
# ===============================

KINH_DICH_QUE = [
    {"name": "Càn (乾)", "meaning": "Trời", "advice": "Hanh thông, lợi về mọi sự, giữ vững chính đạo"},
    {"name": "Khôn (坤)", "meaning": "Đất", "advice": "Thuận theo, ôn hòa, có người dẫn dắt sẽ tốt"},
    {"name": "Truân (屯)", "meaning": "Khó khăn ban đầu", "advice": "Kiên nhẫn, không nên tiến vội"},
    {"name": "Mông (蒙)", "meaning": "Non dại", "advice": "Cần học hỏi, tìm thầy, kiên trì"},
    {"name": "Nhu (需)", "meaning": "Đợi chờ", "advice": "Kiên nhẫn chờ đợi, thời cơ sẽ đến"},
    {"name": "Tụng (訟)", "meaning": "Tranh cãi", "advice": "Nên hòa giải, tránh kiện tụng"},
    {"name": "Sư (師)", "meaning": "Quân đội", "advice": "Cần có người lãnh đạo giỏi"},
    {"name": "Tỷ (比)", "meaning": "Thân cận", "advice": "Tìm đồng minh, kết giao bạn bè"},
    {"name": "Tiểu Súc (小畜)", "meaning": "Tích lũy nhỏ", "advice": "Tích cóp từng chút, chưa nên mạo hiểm"},
    {"name": "Lý (履)", "meaning": "Xử thế", "advice": "Cẩn thận trong hành động"},
    {"name": "Thái (泰)", "meaning": "Thịnh vượng", "advice": "Vạn sự hanh thông, cát tường"},
    {"name": "Bĩ (否)", "meaning": "Bế tắc", "advice": "Thời kỳ khó khăn, nên ẩn nhẫn"},
    {"name": "Đồng Nhân (同人)", "meaning": "Đồng lòng", "advice": "Hợp tác với mọi người sẽ thành công"},
    {"name": "Đại Hữu (大有)", "meaning": "Đại thắng", "advice": "Giàu có, thịnh vượng, nên khiêm tốn"},
    {"name": "Khiêm (謙)", "meaning": "Khiêm tốn", "advice": "Khiêm nhường sẽ được phúc lộc"},
    {"name": "Dự (豫)", "meaning": "Hân hoan", "advice": "Vui vẻ, có lợi trong việc xây dựng"},
    {"name": "Tùy (隨)", "meaning": "Theo đuổi", "advice": "Thuận theo thời thế, uyển chuyển"},
    {"name": "Cổ (蠱)", "meaning": "Sửa chữa", "advice": "Cần sửa đổi những sai lầm cũ"},
    {"name": "Lâm (臨)", "meaning": "Giám sát", "advice": "Đến gần, tiến bước thuận lợi"},
    {"name": "Quan (觀)", "meaning": "Quan sát", "advice": "Nhìn nhận tình hình, suy xét kỹ"},
    {"name": "Phệ Hạp (噬嗑)", "meaning": "Cắn xuyên", "advice": "Kiên quyết xử lý, phân minh"},
    {"name": "Bí (賁)", "meaning": "Trang hoàng", "advice": "Làm đẹp bề ngoài, giữ nội tâm"},
    {"name": "Bác (剝)", "meaning": "Bóc đi", "advice": "Không nên hành động, thời kỳ suy"},
    {"name": "Phục (復)", "meaning": "Trở lại", "advice": "Quay về đúng đường, hồi phục"},
    {"name": "Vô Vọng (無妄)", "meaning": "Không vọng tưởng", "advice": "Hành động đúng đắn, chân thành"},
    {"name": "Đại Súc (大畜)", "meaning": "Tích lũy lớn", "advice": "Thời cơ tốt để phát triển"},
    {"name": "Di (頤)", "meaning": "Nuôi dưỡng", "advice": "Chăm sóc bản thân và người khác"},
    {"name": "Đại Quá (大過)", "meaning": "Vượt quá", "advice": "Cẩn thận, đừng đi quá giới hạn"},
    {"name": "Khảm (坎)", "meaning": "Nước", "advice": "Nguy hiểm, cần thận trọng"},
    {"name": "Ly (離)", "meaning": "Lửa", "advice": "Sáng suốt, bám vào điều đúng đắn"},
    {"name": "Hàm (咸)", "meaning": "Cảm ứng", "advice": "Giao cảm, hòa hợp trong tình cảm"},
    {"name": "Hằng (恆)", "meaning": "Bền vững", "advice": "Kiên trì, giữ vững lập trường"},
]

# ===============================
# DAILY HOROSCOPE TEMPLATES
# ===============================

HOROSCOPE_TEMPLATES = {
    "tinh_yeu": [
        "Hôm nay tình cảm của bạn rất tốt, có thể gặp được người hợp ý.",
        "Cần chú ý lắng nghe đối phương nhiều hơn.",
        "Độc thân có cơ hội gặp người mới, hãy mở lòng.",
        "Tình yêu đang thăng hoa, hãy tận hưởng.",
        "Có thể xảy ra hiểu lầm nhỏ, cần kiên nhẫn giải quyết.",
    ],
    "cong_viec": [
        "Công việc thuận lợi, có thể hoàn thành mục tiêu.",
        "Cần thận trọng trong các quyết định quan trọng.",
        "Có cơ hội thăng tiến, hãy thể hiện năng lực.",
        "Làm việc nhóm sẽ mang lại hiệu quả cao.",
        "Có thể gặp khó khăn nhỏ, nhưng sẽ sớm vượt qua.",
    ],
    "tai_chinh": [
        "Tài chính ổn định, có thể đầu tư nhỏ.",
        "Cẩn thận trong chi tiêu, tránh lãng phí.",
        "Có tin vui về tài chính, có thể nhận được tiền.",
        "Không nên mạo hiểm về tài chính hôm nay.",
        "Cơ hội kiếm thêm thu nhập từ nguồn mới.",
    ],
    "suc_khoe": [
        "Sức khỏe tốt, tinh thần sảng khoái.",
        "Cần nghỉ ngơi đúng giờ, tránh thức khuya.",
        "Nên tập thể dục để tăng cường sức khỏe.",
        "Chú ý đến chế độ ăn uống, ăn nhiều rau xanh.",
        "Có thể hơi mệt mỏi, cần bổ sung năng lượng.",
    ],
}


# ===============================
# TOOL FUNCTIONS
# ===============================


def _get_zodiac_key(day: int, month: int) -> str:
    """Get zodiac key from birth date."""
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "bach_duong"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "kim_nguu"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "song_tu"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "cu_giai"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "su_tu"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "xu_nu"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "thien_binh"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "bo_cap"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "nhan_ma"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "ma_ket"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "bao_binh"
    else:
        return "song_ngu"


def _get_element_from_menh(menh: str) -> str:
    """Extract element from menh name."""
    if "Kim" in menh:
        return "Kim"
    elif "Mộc" in menh:
        return "Mộc"
    elif "Thủy" in menh:
        return "Thủy"
    elif "Hỏa" in menh:
        return "Hỏa"
    else:
        return "Thổ"


def _get_menh_nam_sinh(nam: int) -> str:
    """Get menh from birth year."""
    for years, menh in NGU_HANH_MENH.items():
        if nam in years:
            return menh
    # Fallback using cycle
    cycle_year = (nam - 1924) % 60
    cycle_map = [
        "Hải Trung Kim", "Hải Trung Kim", "Lô Trung Hỏa", "Lô Trung Hỏa",
        "Đại Lâm Mộc", "Đại Lâm Mộc", "Lộ Bàng Thổ", "Lộ Bàng Thổ",
        "Kiếm Phong Kim", "Kiếm Phong Kim", "Sơn Đầu Hỏa", "Sơn Đầu Hỏa",
        "Giản Hạ Thủy", "Giản Hạ Thủy", "Thành Đầu Thổ", "Thành Đầu Thổ",
        "Bạch Lạp Kim", "Bạch Lạp Kim", "Dương Liễu Mộc", "Dương Liễu Mộc",
        "Tuyền Trung Thủy", "Tuyền Trung Thủy", "Ốc Thượng Thổ", "Ốc Thượng Thổ",
        "Tích Lịch Hỏa", "Tích Lịch Hỏa", "Tùng Bách Mộc", "Tùng Bách Mộc",
        "Trường Lưu Thủy", "Trường Lưu Thủy", "Sa Trung Kim", "Sa Trung Kim",
        "Sơn Hạ Hỏa", "Sơn Hạ Hỏa", "Bình Địa Mộc", "Bình Địa Mộc",
        "Bích Thượng Thổ", "Bích Thượng Thổ", "Kim Bạc Kim", "Kim Bạc Kim",
        "Phú Đăng Hỏa", "Phú Đăng Hỏa", "Thiên Hà Thủy", "Thiên Hà Thủy",
        "Đại Trạch Thổ", "Đại Trạch Thổ", "Thoa Xuyến Kim", "Thoa Xuyến Kim",
        "Tang Đố Mộc", "Tang Đố Mộc", "Đại Khe Thủy", "Đại Khe Thủy",
        "Sa Trung Thổ", "Sa Trung Thổ", "Thiên Thượng Hỏa", "Thiên Thượng Hỏa",
        "Thạch Lựu Mộc", "Thạch Lựu Mộc", "Đại Hải Thủy", "Đại Hải Thủy",
    ]
    return cycle_map[cycle_year % len(cycle_map)]


def xem_cung_hoang_dao(ngay_sinh: int, thang_sinh: int) -> Dict[str, Any]:
    """Xem cung hoàng đạo từ ngày tháng sinh.

    Tra cứu cung hoàng đạo dựa trên ngày và tháng sinh, cung cấp thông tin
    về tính cách, đặc điểm và các cung tương hợp.

    Args:
        ngay_sinh: Ngày sinh (1-31)
        thang_sinh: Tháng sinh (1-12)

    Returns:
        Dict chứa thông tin cung hoàng đạo: tên, biểu tượng, nguyên tố,
        đặc điểm tính cách, các cung tương hợp, màu và số may mắn.

    Examples:
        >>> xem_cung_hoang_dao(15, 6)
        {'success': True, 'zodiac': {'name': 'Song Tử', ...}}
    """
    try:
        if not (1 <= ngay_sinh <= 31) or not (1 <= thang_sinh <= 12):
            return {"success": False, "error": "Ngày hoặc tháng không hợp lệ"}

        zodiac_key = _get_zodiac_key(ngay_sinh, thang_sinh)
        zodiac = ZODIAC_SIGNS[zodiac_key]

        logger.info(f"Xem cung hoàng đạo: {ngay_sinh}/{thang_sinh} -> {zodiac['name']}")

        return {
            "success": True,
            "zodiac": {
                "ten": zodiac["name"],
                "tieng_anh": zodiac["english"],
                "bieu_tuong": zodiac["symbol"],
                "nguyen_to": zodiac["element"],
                "ngay_sinh": zodiac["dates"],
                "dac_diem": zodiac["traits"],
                "tuong_hop": [ZODIAC_SIGNS.get(z, {}).get("name", z) for z in zodiac["compatible"][:2]],
                "mau_may_man": zodiac["lucky_colors"],
                "so_may_man": zodiac["lucky_numbers"],
            }
        }
    except Exception as e:
        logger.error(f"Lỗi xem cung hoàng đạo: {e}")
        return {"success": False, "error": str(e)}


def xem_con_giap(nam_sinh: int) -> Dict[str, Any]:
    """Xem con giáp theo năm sinh.

    Xác định con giáp (12 con giáp) dựa trên năm sinh và cung cấp
    thông tin về đặc điểm tính cách của con giáp đó.

    Args:
        nam_sinh: Năm sinh dương lịch (ví dụ: 1990, 2000)

    Returns:
        Dict chứa thông tin con giáp: tên chi, con vật, đặc điểm tính cách.

    Examples:
        >>> xem_con_giap(1990)
        {'success': True, 'con_giap': {'chi': 'Ngọ', 'con_vat': 'Ngựa', ...}}
    """
    try:
        index = nam_sinh % 12
        giap = CON_GIAP[index]

        logger.info(f"Xem con giáp: {nam_sinh} -> {giap['animal']}")

        return {
            "success": True,
            "con_giap": {
                "nam_sinh": nam_sinh,
                "chi": giap["name"],
                "con_vat": giap["animal"],
                "dac_diem": giap["traits"],
                "nam_tot": [nam_sinh + 12, nam_sinh + 24],
                "nam_han": [nam_sinh + 6, nam_sinh + 18],
            }
        }
    except Exception as e:
        logger.error(f"Lỗi xem con giáp: {e}")
        return {"success": False, "error": str(e)}


def xem_menh_ngu_hanh(nam_sinh: int) -> Dict[str, Any]:
    """Xem mệnh ngũ hành theo năm sinh.

    Xác định mệnh ngũ hành (Kim, Mộc, Thủy, Hỏa, Thổ) dựa trên năm sinh
    và cung cấp thông tin về màu sắc, hướng may mắn.

    Args:
        nam_sinh: Năm sinh dương lịch (ví dụ: 1990, 2000)

    Returns:
        Dict chứa thông tin mệnh: tên mệnh, nguyên tố, màu may mắn,
        hướng tốt, các mệnh tương sinh/tương khắc.

    Examples:
        >>> xem_menh_ngu_hanh(1990)
        {'success': True, 'menh': {'ten': 'Lộ Bàng Thổ', 'nguyen_to': 'Thổ', ...}}
    """
    try:
        menh = _get_menh_nam_sinh(nam_sinh)
        element = _get_element_from_menh(menh)
        element_info = NGU_HANH_ELEMENT.get(element, {})

        logger.info(f"Xem mệnh ngũ hành: {nam_sinh} -> {menh}")

        return {
            "success": True,
            "menh": {
                "nam_sinh": nam_sinh,
                "ten_menh": menh,
                "nguyen_to": element,
                "mau_may_man": element_info.get("color", []),
                "huong_tot": element_info.get("direction", ""),
                "mua_tot": element_info.get("season", ""),
                "tuong_sinh_voi": TUONG_SINH.get(element, ""),
                "tuong_khac_voi": TUONG_KHAC.get(element, ""),
                "bi_khac_boi": [k for k, v in TUONG_KHAC.items() if v == element],
            }
        }
    except Exception as e:
        logger.error(f"Lỗi xem mệnh ngũ hành: {e}")
        return {"success": False, "error": str(e)}


def xem_tuoi_hop_nhau(nam_sinh_1: int, nam_sinh_2: int) -> Dict[str, Any]:
    """Xem hai tuổi có hợp nhau không.

    Phân tích mức độ tương hợp giữa hai người dựa trên năm sinh,
    xét theo con giáp và ngũ hành.

    Args:
        nam_sinh_1: Năm sinh người thứ nhất
        nam_sinh_2: Năm sinh người thứ hai

    Returns:
        Dict chứa phân tích: con giáp, mệnh của 2 người và kết quả tương hợp.

    Examples:
        >>> xem_tuoi_hop_nhau(1990, 1995)
        {'success': True, 'ket_qua': {'tuong_hop': True, ...}}
    """
    try:
        # Lấy con giáp
        giap1 = CON_GIAP[nam_sinh_1 % 12]
        giap2 = CON_GIAP[nam_sinh_2 % 12]

        # Lấy mệnh
        menh1 = _get_menh_nam_sinh(nam_sinh_1)
        menh2 = _get_menh_nam_sinh(nam_sinh_2)
        element1 = _get_element_from_menh(menh1)
        element2 = _get_element_from_menh(menh2)

        # Phân tích tương hợp ngũ hành
        hop_ngu_hanh = False
        mo_ta_ngu_hanh = ""

        if element1 == element2:
            hop_ngu_hanh = True
            mo_ta_ngu_hanh = f"Cùng mệnh {element1}, hòa hợp tốt"
        elif TUONG_SINH.get(element1) == element2:
            hop_ngu_hanh = True
            mo_ta_ngu_hanh = f"{element1} sinh {element2}, rất tốt"
        elif TUONG_SINH.get(element2) == element1:
            hop_ngu_hanh = True
            mo_ta_ngu_hanh = f"{element2} sinh {element1}, rất tốt"
        elif TUONG_KHAC.get(element1) == element2:
            hop_ngu_hanh = False
            mo_ta_ngu_hanh = f"{element1} khắc {element2}, cần cẩn thận"
        elif TUONG_KHAC.get(element2) == element1:
            hop_ngu_hanh = False
            mo_ta_ngu_hanh = f"{element2} khắc {element1}, cần cẩn thận"
        else:
            hop_ngu_hanh = True
            mo_ta_ngu_hanh = "Không tương sinh cũng không tương khắc, ổn"

        # Điểm tương hợp tổng thể
        diem = 70 if hop_ngu_hanh else 50
        if giap1["animal"] == giap2["animal"]:
            diem += 10

        logger.info(f"Xem tuổi hợp nhau: {nam_sinh_1} & {nam_sinh_2} -> {diem}%")

        return {
            "success": True,
            "ket_qua": {
                "nguoi_1": {
                    "nam_sinh": nam_sinh_1,
                    "con_giap": giap1["animal"],
                    "menh": menh1,
                    "nguyen_to": element1,
                },
                "nguoi_2": {
                    "nam_sinh": nam_sinh_2,
                    "con_giap": giap2["animal"],
                    "menh": menh2,
                    "nguyen_to": element2,
                },
                "phan_tich_ngu_hanh": mo_ta_ngu_hanh,
                "tuong_hop": hop_ngu_hanh,
                "diem_tuong_hop": diem,
                "loi_khuyen": "Hãy yêu thương và thấu hiểu nhau để vượt qua mọi khó khăn" if not hop_ngu_hanh else "Hai bạn rất hợp nhau, hãy trân trọng!",
            }
        }
    except Exception as e:
        logger.error(f"Lỗi xem tuổi hợp nhau: {e}")
        return {"success": False, "error": str(e)}


def boi_que_kinh_dich() -> Dict[str, Any]:
    """Bói quẻ Kinh Dịch ngẫu nhiên.

    Gieo một quẻ Kinh Dịch ngẫu nhiên và cung cấp lời giải thích,
    lời khuyên cho quẻ đó.

    Returns:
        Dict chứa thông tin quẻ: tên quẻ, ý nghĩa và lời khuyên.

    Examples:
        >>> boi_que_kinh_dich()
        {'success': True, 'que': {'ten': 'Càn (乾)', 'y_nghia': 'Trời', ...}}
    """
    try:
        que = random.choice(KINH_DICH_QUE)

        logger.info(f"Bói quẻ Kinh Dịch: {que['name']}")

        return {
            "success": True,
            "que": {
                "ten": que["name"],
                "y_nghia": que["meaning"],
                "loi_khuyen": que["advice"],
                "thoi_gian": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        }
    except Exception as e:
        logger.error(f"Lỗi bói quẻ: {e}")
        return {"success": False, "error": str(e)}


def xem_so_may_man(ngay_sinh: int, thang_sinh: int, nam_sinh: int) -> Dict[str, Any]:
    """Tính số may mắn từ ngày tháng năm sinh.

    Tính toán các con số may mắn dựa trên ngày tháng năm sinh,
    và gợi ý màu sắc may mắn.

    Args:
        ngay_sinh: Ngày sinh (1-31)
        thang_sinh: Tháng sinh (1-12)
        nam_sinh: Năm sinh (ví dụ: 1990)

    Returns:
        Dict chứa các số may mắn và màu may mắn.

    Examples:
        >>> xem_so_may_man(15, 6, 1990)
        {'success': True, 'so_may_man': [6, 15, 21, ...], ...}
    """
    try:
        # Tính số chủ đạo (life path number)
        total = ngay_sinh + thang_sinh + sum(int(d) for d in str(nam_sinh))
        while total > 9:
            total = sum(int(d) for d in str(total))

        # Các số may mắn
        so_may_man = sorted(set([
            total,
            ngay_sinh,
            (ngay_sinh + thang_sinh) % 10 or 10,
            (nam_sinh % 100) % 10 or 10,
            total * 2 if total * 2 <= 49 else total,
        ]))

        # Màu may mắn dựa trên số chủ đạo
        mau_theo_so = {
            1: ["Đỏ", "Vàng gold"],
            2: ["Cam", "Xanh lá nhạt"],
            3: ["Vàng", "Tím"],
            4: ["Xanh lá", "Nâu"],
            5: ["Xanh dương", "Xám"],
            6: ["Hồng", "Xanh ngọc"],
            7: ["Tím", "Bạc"],
            8: ["Đen", "Đỏ đậm"],
            9: ["Trắng", "Vàng"],
        }

        logger.info(f"Xem số may mắn: {ngay_sinh}/{thang_sinh}/{nam_sinh}")

        return {
            "success": True,
            "so_chu_dao": total,
            "so_may_man": so_may_man,
            "mau_may_man": mau_theo_so.get(total, ["Trắng"]),
            "ngay_tot_trong_thang": [total, total + 9, total + 18] if total + 18 <= 31 else [total, total + 9],
        }
    except Exception as e:
        logger.error(f"Lỗi xem số may mắn: {e}")
        return {"success": False, "error": str(e)}


def du_bao_ngay_hom_nay(cung_hoang_dao: str = "") -> Dict[str, Any]:
    """Dự báo vận trình ngày hôm nay theo cung hoàng đạo.

    Cung cấp dự báo về tình yêu, công việc, tài chính và sức khỏe
    cho ngày hôm nay dựa trên cung hoàng đạo.

    Args:
        cung_hoang_dao: Tên cung hoàng đạo (ví dụ: "bach_duong", "kim_nguu", 
            "song_tu", "cu_giai", "su_tu", "xu_nu", "thien_binh", 
            "bo_cap", "nhan_ma", "ma_ket", "bao_binh", "song_ngu").
            Có thể dùng tên tiếng Việt như "Bạch Dương", "Song Tử".
            Nếu để trống, sẽ dự báo chung.

    Returns:
        Dict chứa dự báo về các mặt: tình yêu, công việc, tài chính, sức khỏe.

    Examples:
        >>> du_bao_ngay_hom_nay("song_tu")
        {'success': True, 'du_bao': {'tinh_yeu': '...', ...}}
    """
    try:
        # Normalize cung hoang dao name
        cung_key = cung_hoang_dao.lower().replace(" ", "_").replace("ư", "u").replace("ử", "u")
        
        # Map Vietnamese names to keys
        name_map = {
            "bạch_dương": "bach_duong", "bạch dương": "bach_duong",
            "kim_ngưu": "kim_nguu", "kim ngưu": "kim_nguu",
            "song_tử": "song_tu", "song tử": "song_tu",
            "cự_giải": "cu_giai", "cự giải": "cu_giai",
            "sư_tử": "su_tu", "sư tử": "su_tu",
            "xử_nữ": "xu_nu", "xử nữ": "xu_nu",
            "thiên_bình": "thien_binh", "thiên bình": "thien_binh",
            "bọ_cạp": "bo_cap", "bọ cạp": "bo_cap",
            "nhân_mã": "nhan_ma", "nhân mã": "nhan_ma",
            "ma_kết": "ma_ket", "ma kết": "ma_ket",
            "bảo_bình": "bao_binh", "bảo bình": "bao_binh",
            "song_ngư": "song_ngu", "song ngư": "song_ngu",
        }
        
        cung_key = name_map.get(cung_key, cung_key)
        
        zodiac_info = ZODIAC_SIGNS.get(cung_key, {})
        zodiac_name = zodiac_info.get("name", cung_hoang_dao or "Chung")

        # Random predictions for today
        random.seed(datetime.now().strftime("%Y%m%d") + cung_key)

        du_bao = {
            "tinh_yeu": random.choice(HOROSCOPE_TEMPLATES["tinh_yeu"]),
            "cong_viec": random.choice(HOROSCOPE_TEMPLATES["cong_viec"]),
            "tai_chinh": random.choice(HOROSCOPE_TEMPLATES["tai_chinh"]),
            "suc_khoe": random.choice(HOROSCOPE_TEMPLATES["suc_khoe"]),
        }

        # Điểm tổng quan
        diem = random.randint(60, 95)

        logger.info(f"Dự báo ngày hôm nay cho: {zodiac_name}")

        return {
            "success": True,
            "cung_hoang_dao": zodiac_name,
            "ngay": datetime.now().strftime("%d/%m/%Y"),
            "diem_tong_quan": diem,
            "du_bao": du_bao,
            "loi_khuyen_ngay": "Hãy giữ tinh thần lạc quan và tích cực trong mọi việc!",
        }
    except Exception as e:
        logger.error(f"Lỗi dự báo ngày: {e}")
        return {"success": False, "error": str(e)}


def xem_ngay_tot_xau(ngay: int, thang: int, nam: int) -> Dict[str, Any]:
    """Xem ngày tốt xấu theo âm lịch.

    Phân tích ngày theo âm lịch để xác định các việc nên làm
    và không nên làm trong ngày đó.

    Args:
        ngay: Ngày âm lịch (1-30)
        thang: Tháng âm lịch (1-12)
        nam: Năm dương lịch để tham chiếu

    Returns:
        Dict chứa thông tin ngày: loại ngày, việc nên/không nên làm.

    Examples:
        >>> xem_ngay_tot_xau(15, 1, 2024)
        {'success': True, 'ngay': {'loai': 'Tốt', 'nen_lam': [...], ...}}
    """
    try:
        if not (1 <= ngay <= 30) or not (1 <= thang <= 12):
            return {"success": False, "error": "Ngày hoặc tháng âm lịch không hợp lệ"}

        # Các ngày đặc biệt trong tháng
        ngay_ram = ngay == 15
        ngay_mung_mot = ngay == 1
        ngay_30 = ngay == 30

        # Danh sách việc
        viec_tot = [
            "Cầu tài", "Khai trương", "Xuất hành", "Giao dịch",
            "Ký kết hợp đồng", "Cưới hỏi", "Động thổ", "Nhập trạch",
            "Khai nghiệp", "Cầu phúc", "Gieo trồng", "Thu hoạch",
        ]
        
        viec_xau = [
            "Khởi công xây dựng", "Kiện cáo", "Đi xa", "Phá dỡ",
            "Khai mộ", "Cắt may", "Sửa nhà", "Đào ao",
        ]

        # Phân tích ngày
        random.seed(f"{ngay}{thang}{nam}")
        
        if ngay_ram or ngay_mung_mot:
            loai_ngay = "Rất Tốt"
            nen_lam = random.sample(viec_tot, min(6, len(viec_tot)))
            khong_nen = random.sample(viec_xau, 2)
            gio_tot = ["Mão (5h-7h)", "Ngọ (11h-13h)", "Dậu (17h-19h)"]
        elif ngay_30:
            loai_ngay = "Trung Bình"
            nen_lam = random.sample(viec_tot, 3)
            khong_nen = random.sample(viec_xau, 4)
            gio_tot = ["Thìn (7h-9h)", "Mùi (13h-15h)"]
        elif ngay in [5, 14, 23]:
            loai_ngay = "Xấu"
            nen_lam = ["Nghỉ ngơi", "Tu tập", "Làm việc nhà"]
            khong_nen = random.sample(viec_xau, 5) + random.sample(viec_tot[:4], 2)
            gio_tot = ["Sửu (1h-3h)"]
        else:
            loai_ngay = "Tốt" if ngay % 2 == 1 else "Bình thường"
            nen_lam = random.sample(viec_tot, 4)
            khong_nen = random.sample(viec_xau, 3)
            gio_tot = ["Mão (5h-7h)", "Thân (15h-17h)"]

        huong_tot = random.choice(["Đông", "Tây", "Nam", "Bắc", "Đông Nam", "Tây Bắc"])

        logger.info(f"Xem ngày tốt xấu: {ngay}/{thang} âm lịch -> {loai_ngay}")

        return {
            "success": True,
            "ngay_am_lich": f"{ngay}/{thang}",
            "nam_tham_chieu": nam,
            "loai_ngay": loai_ngay,
            "gio_tot": gio_tot,
            "huong_xuat_hanh": huong_tot,
            "nen_lam": nen_lam,
            "khong_nen_lam": khong_nen,
            "ghi_chu": "Ngày Rằm và Mùng 1 là ngày tốt để cúng bái, cầu phúc" if ngay_ram or ngay_mung_mot else "",
        }
    except Exception as e:
        logger.error(f"Lỗi xem ngày tốt xấu: {e}")
        return {"success": False, "error": str(e)}
