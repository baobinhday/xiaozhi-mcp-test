"""Numerology (Thần Số Học) tool functions.

Provides numerology calculations based on Pythagorean system:
- Life Path Number (Số chủ đạo)
- Destiny Number (Số sứ mệnh)
- Soul Urge Number (Số linh hồn)
- Personality Number (Số nhân cách)
- Personal Year (Năm cá nhân)
- Full Profile (Tổng hợp)
"""

import logging
import unicodedata
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("numerology_tools")

# ===============================
# PYTHAGOREAN LETTER-TO-NUMBER MAP
# ===============================

LETTER_VALUES = {
    'A': 1, 'J': 1, 'S': 1,
    'B': 2, 'K': 2, 'T': 2,
    'C': 3, 'L': 3, 'U': 3,
    'D': 4, 'M': 4, 'V': 4,
    'E': 5, 'N': 5, 'W': 5,
    'F': 6, 'O': 6, 'X': 6,
    'G': 7, 'P': 7, 'Y': 7,
    'H': 8, 'Q': 8, 'Z': 8,
    'I': 9, 'R': 9,
}

VOWELS = set('AEIOU')
# Y is considered vowel when it's the only vowel sound in a syllable,
# but for simplicity we treat it as consonant in Pythagorean system

# ===============================
# MASTER NUMBERS
# ===============================

MASTER_NUMBERS = {11, 22, 33}

# ===============================
# NUMBER MEANINGS (Ý nghĩa các con số)
# ===============================

NUMBER_MEANINGS = {
    1: {
        "name": "Người tiên phong",
        "keywords": ["Độc lập", "Sáng tạo", "Lãnh đạo", "Quyết đoán"],
        "strengths": "Tự tin, có tầm nhìn, tinh thần tiên phong",
        "challenges": "Bướng bỉnh, ích kỷ, thiếu kiên nhẫn",
        "weakness": "Hay cô đơn vì quá độc lập, đôi khi áp đặt ý kiến lên người khác, khó chấp nhận sai lầm",
        "love": "Thích dẫn dắt trong mối quan hệ, cần đối tác tôn trọng không gian riêng, chân thành nhưng đôi khi thiếu lãng mạn",
        "message": "Hãy học cách lắng nghe và hợp tác. Sức mạnh thật sự nằm ở việc biết khi nào cần tiến và khi nào cần lùi.",
        "career": ["Doanh nhân", "Giám đốc", "Nhà phát minh", "Freelancer"],
    },
    2: {
        "name": "Người hòa giải",
        "keywords": ["Hợp tác", "Nhạy cảm", "Ngoại giao", "Kiên nhẫn"],
        "strengths": "Tinh tế, biết lắng nghe, giỏi làm việc nhóm",
        "challenges": "Thiếu quyết đoán, dễ bị tổn thương, phụ thuộc",
        "weakness": "Dễ đánh mất bản thân vì muốn làm hài lòng người khác, sợ xung đột, hay do dự",
        "love": "Lãng mạn và chu đáo, cần sự ổn định và an toàn, đối tác lý tưởng là người biết trân trọng sự nhạy cảm của bạn",
        "message": "Đừng quên yêu thương bản thân. Sự hòa hợp bắt đầu từ việc cân bằng giữa nhu cầu của mình và người khác.",
        "career": ["Nhà tư vấn", "Trung gian", "Nghệ sĩ", "Nhà trị liệu"],
    },
    3: {
        "name": "Người sáng tạo",
        "keywords": ["Sáng tạo", "Giao tiếp", "Lạc quan", "Nghệ thuật"],
        "strengths": "Vui vẻ, có khiếu biểu đạt, truyền cảm hứng",
        "challenges": "Thiếu tập trung, nông cạn, hay lo lắng",
        "weakness": "Dễ bị phân tán, đôi khi hời hợt trong cảm xúc, khó hoàn thành những gì đã bắt đầu",
        "love": "Vui vẻ và đầy sức sống, thích những mối quan hệ thú vị, cần đối tác biết thưởng thức niềm vui sống",
        "message": "Tập trung năng lượng sáng tạo của bạn vào một vài mục tiêu quan trọng. Chiều sâu sẽ mang lại thành công bền vững.",
        "career": ["Nghệ sĩ", "Nhà văn", "Diễn giả", "Thiết kế"],
    },
    4: {
        "name": "Người xây dựng",
        "keywords": ["Ổn định", "Thực tế", "Kỷ luật", "Chăm chỉ"],
        "strengths": "Đáng tin cậy, có tổ chức, kiên trì",
        "challenges": "Cứng nhắc, bảo thủ, làm việc quá sức",
        "weakness": "Khó thích nghi với thay đổi, hay lo lắng về an toàn, đôi khi quá nghiêm khắc với bản thân và người khác",
        "love": "Trung thành và đáng tin cậy, thích sự ổn định lâu dài, thể hiện tình yêu qua hành động hơn lời nói",
        "message": "Hãy cho phép mình linh hoạt hơn. Cuộc sống cần cả nền tảng vững chắc lẫn những khoảnh khắc bất ngờ.",
        "career": ["Kỹ sư", "Kế toán", "Kiến trúc sư", "Quản lý"],
    },
    5: {
        "name": "Người tự do",
        "keywords": ["Tự do", "Phiêu lưu", "Linh hoạt", "Đa năng"],
        "strengths": "Thích nghi tốt, tò mò, năng động",
        "challenges": "Thiếu cam kết, bồn chồn, thiếu trách nhiệm",
        "weakness": "Sợ bị ràng buộc, dễ chán nản, đôi khi thiếu sự kiên định trong quyết định",
        "love": "Cần không gian tự do trong mối quan hệ, thích những cuộc phiêu lưu cùng nhau, đối tác lý tưởng là người cởi mở và linh hoạt",
        "message": "Tự do thật sự đến từ việc biết cam kết với điều quan trọng. Hãy tìm sự cân bằng giữa phiêu lưu và ổn định.",
        "career": ["Du lịch", "Bán hàng", "Báo chí", "Marketing"],
    },
    6: {
        "name": "Người nuôi dưỡng",
        "keywords": ["Trách nhiệm", "Yêu thương", "Gia đình", "Hài hòa"],
        "strengths": "Chu đáo, có trách nhiệm, biết quan tâm",
        "challenges": "Can thiệp quá mức, lo lắng, hy sinh quá nhiều",
        "weakness": "Hay kiểm soát người thân vì lo lắng, quên chăm sóc bản thân, đôi khi mong đợi sự đền đáp",
        "love": "Yêu thương sâu sắc và hết mình, coi trọng gia đình, đối tác cần biết trân trọng sự hy sinh của bạn",
        "message": "Yêu thương người khác bắt đầu từ yêu thương bản thân. Hãy học cách cho đi mà không cần nhận lại.",
        "career": ["Y tế", "Giáo viên", "Tư vấn", "Vệ sĩ"],
    },
    7: {
        "name": "Người tìm kiếm",
        "keywords": ["Trí tuệ", "Phân tích", "Tâm linh", "Nội tâm"],
        "strengths": "Sâu sắc, trực giác mạnh, có chiều sâu tư duy",
        "challenges": "Cô đơn, hoài nghi, khó gần",
        "weakness": "Hay cách ly khỏi thế giới, quá phân tích mọi thứ, khó tin tưởng người khác hoàn toàn",
        "love": "Cần đối tác hiểu và tôn trọng nhu cầu riêng tư, tình yêu sâu sắc nhưng cần thời gian để mở lòng",
        "message": "Tri thức là sức mạnh, nhưng kết nối với người khác cũng quan trọng không kém. Hãy mở lòng đón nhận.",
        "career": ["Nhà nghiên cứu", "Triết gia", "Nhà khoa học", "Tâm linh"],
    },
    8: {
        "name": "Người thành đạt",
        "keywords": ["Quyền lực", "Thành công", "Vật chất", "Tham vọng"],
        "strengths": "Có tầm nhìn kinh doanh, quyết đoán, mạnh mẽ",
        "challenges": "Tham công tiếc việc, kiểm soát, vật chất hóa",
        "weakness": "Hay đặt công việc lên trên mối quan hệ, đôi khi cứng nhắc trong cách quản lý, dễ bị stress",
        "love": "Trung thành và bảo vệ người yêu, thể hiện tình yêu qua sự chu cấp, cần đối tác hiểu tham vọng của mình",
        "message": "Thành công thật sự bao gồm cả hạnh phúc cá nhân. Hãy nhớ rằng tiền bạc và quyền lực không thể mua được tình yêu thương.",
        "career": ["Doanh nhân", "Tài chính", "Luật sư", "Chính trị gia"],
    },
    9: {
        "name": "Người nhân đạo",
        "keywords": ["Nhân đạo", "Bao dung", "Lý tưởng", "Nghệ thuật"],
        "strengths": "Rộng lượng, có lý tưởng, sáng tạo",
        "challenges": "Mơ mộng, thiếu thực tế, hy sinh quá mức",
        "weakness": "Hay bỏ qua nhu cầu bản thân, đôi khi lý tưởng hóa mọi thứ, khó buông bỏ quá khứ",
        "love": "Yêu thương vô điều kiện, lãng mạn và lý tưởng, cần đối tác chia sẻ giá trị nhân văn",
        "message": "Hãy học cách buông bỏ để đón nhận cái mới. Sự hoàn thiện đến từ việc chấp nhận những khiếm khuyết.",
        "career": ["Từ thiện", "Nghệ thuật", "Giáo dục", "Y tế"],
    },
    11: {
        "name": "Bậc thầy trực giác (Master Number)",
        "keywords": ["Trực giác", "Tâm linh", "Truyền cảm hứng", "Khai sáng"],
        "strengths": "Trực giác mạnh, có tầm nhìn, khả năng chữa lành",
        "challenges": "Căng thẳng, lo lắng, kỳ vọng cao",
        "weakness": "Dễ bị quá tải năng lượng, hay cảm thấy khác biệt với mọi người, đôi khi mất kết nối thực tế",
        "love": "Tìm kiếm mối quan hệ tâm linh sâu sắc, cần đối tác hiểu được chiều sâu tâm hồn, yêu thương mãnh liệt",
        "message": "Bạn mang theo sứ mệnh đặc biệt. Hãy tin vào trực giác nhưng cũng cần giữ vững kết nối với thực tế.",
        "career": ["Nhà tâm linh", "Nhà trị liệu", "Nghệ sĩ", "Diễn giả"],
    },
    22: {
        "name": "Bậc thầy xây dựng (Master Number)",
        "keywords": ["Xây dựng", "Tầm nhìn lớn", "Thực hiện", "Di sản"],
        "strengths": "Biến ước mơ thành hiện thực, tầm nhìn xa, kiên định",
        "challenges": "Áp lực lớn, kỳ vọng quá cao, kiệt sức",
        "weakness": "Hay đặt tiêu chuẩn quá cao cho bản thân, dễ bị kiệt sức vì gánh vác quá nhiều, khó chấp nhận thất bại",
        "love": "Tìm kiếm đối tác chia sẻ tầm nhìn lớn, trung thành và cam kết, thể hiện tình yêu qua việc xây dựng tương lai chung",
        "message": "Bạn có khả năng tạo ra di sản vĩ đại. Hãy nhớ nghỉ ngơi và chia sẻ gánh nặng với người khác.",
        "career": ["Kiến trúc sư", "CEO", "Chính trị gia", "Nhà từ thiện lớn"],
    },
    33: {
        "name": "Bậc thầy chữa lành (Master Number)",
        "keywords": ["Chữa lành", "Phụng sự", "Hy sinh", "Tình yêu vô điều kiện"],
        "strengths": "Yêu thương vô điều kiện, khả năng chữa lành, truyền cảm hứng",
        "challenges": "Gánh nặng trách nhiệm, tự hy sinh quá mức",
        "weakness": "Hay quên bản thân vì phụng sự người khác, đôi khi cảm thấy mệt mỏi vì gánh vác quá nhiều, khó từ chối",
        "love": "Yêu thương vô điều kiện và hy sinh cao cả, tìm kiếm mối quan hệ tâm linh, đối tác cần biết trân trọng trái tim lớn của bạn",
        "message": "Bạn là nguồn sáng cho thế giới. Nhưng hãy nhớ rằng để tiếp tục tỏa sáng, bạn cần chăm sóc ngọn lửa bên trong mình.",
        "career": ["Nhà trị liệu", "Nhà tâm linh", "Thầy giáo", "Nhà từ thiện"],
    },
}


# ===============================
# HELPER FUNCTIONS
# ===============================


def _normalize_name(name: str) -> str:
    """Normalize Vietnamese name to ASCII for numerology calculation."""
    # Remove diacritics from Vietnamese characters
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Convert to uppercase and remove non-letters
    return ''.join(c.upper() for c in ascii_name if c.isalpha())


def _reduce_to_single(num: int, keep_master: bool = True) -> int:
    """Reduce a number to single digit, optionally keeping master numbers."""
    while num > 9:
        if keep_master and num in MASTER_NUMBERS:
            return num
        num = sum(int(d) for d in str(num))
    return num


def _name_to_number(name: str) -> int:
    """Convert name to number using Pythagorean system."""
    normalized = _normalize_name(name)
    total = sum(LETTER_VALUES.get(c, 0) for c in normalized)
    return total


def _get_vowels_value(name: str) -> int:
    """Get sum of vowel values in name."""
    normalized = _normalize_name(name)
    total = sum(LETTER_VALUES.get(c, 0) for c in normalized if c in VOWELS)
    return total


def _get_consonants_value(name: str) -> int:
    """Get sum of consonant values in name."""
    normalized = _normalize_name(name)
    total = sum(LETTER_VALUES.get(c, 0) for c in normalized if c not in VOWELS)
    return total


def _get_number_meaning(num: int) -> Dict[str, Any]:
    """Get meaning for a given number."""
    return NUMBER_MEANINGS.get(num, NUMBER_MEANINGS.get(_reduce_to_single(num, False), {}))


# ===============================
# TOOL FUNCTIONS
# ===============================


def life_path(ngay_sinh: int, thang_sinh: int, nam_sinh: int) -> Dict[str, Any]:
    """Tính số chủ đạo (Life Path Number) từ ngày tháng năm sinh.

    Số chủ đạo là con số quan trọng nhất trong thần số học, thể hiện 
    mục đích sống và con đường vận mệnh của bạn.

    Args:
        ngay_sinh: Ngày sinh (1-31)
        thang_sinh: Tháng sinh (1-12)
        nam_sinh: Năm sinh (ví dụ: 1990)

    Returns:
        Dict chứa số chủ đạo và ý nghĩa của nó.

    Examples:
        >>> life_path(15, 6, 1990)
        {'success': True, 'so_chu_dao': 4, 'y_nghia': {...}}
    """
    try:
        if not (1 <= ngay_sinh <= 31) or not (1 <= thang_sinh <= 12):
            return {"success": False, "error": "Ngày hoặc tháng không hợp lệ"}

        # Reduce day, month, year separately first, then add and reduce again
        day_reduced = _reduce_to_single(ngay_sinh, keep_master=True)
        month_reduced = _reduce_to_single(thang_sinh, keep_master=True)
        year_reduced = _reduce_to_single(sum(int(d) for d in str(nam_sinh)), keep_master=True)
        
        total = day_reduced + month_reduced + year_reduced
        life_path_num = _reduce_to_single(total, keep_master=True)
        
        meaning = _get_number_meaning(life_path_num)

        logger.info(f"Life Path: {ngay_sinh}/{thang_sinh}/{nam_sinh} -> {life_path_num}")

        return {
            "success": True,
            "so_chu_dao": life_path_num,
            "ngay_sinh": f"{ngay_sinh}/{thang_sinh}/{nam_sinh}",
            "la_master_number": life_path_num in MASTER_NUMBERS,
            "y_nghia": meaning,
        }
    except Exception as e:
        logger.error(f"Lỗi tính số chủ đạo: {e}")
        return {"success": False, "error": str(e)}


def destiny(ho_ten: str) -> Dict[str, Any]:
    """Tính số sứ mệnh (Destiny/Expression Number) từ họ tên đầy đủ.

    Số sứ mệnh thể hiện tài năng, khả năng tiềm ẩn và những gì bạn 
    có thể đạt được trong cuộc sống.

    Args:
        ho_ten: Họ tên đầy đủ (ví dụ: "Nguyễn Văn A")

    Returns:
        Dict chứa số sứ mệnh và ý nghĩa của nó.

    Examples:
        >>> destiny("Nguyen Van A")
        {'success': True, 'so_su_menh': 7, 'y_nghia': {...}}
    """
    try:
        if not ho_ten or not ho_ten.strip():
            return {"success": False, "error": "Họ tên không được để trống"}

        total = _name_to_number(ho_ten)
        destiny_num = _reduce_to_single(total, keep_master=True)
        meaning = _get_number_meaning(destiny_num)

        logger.info(f"Destiny: {ho_ten} -> {destiny_num}")

        return {
            "success": True,
            "ho_ten": ho_ten,
            "ho_ten_chuan_hoa": _normalize_name(ho_ten),
            "so_su_menh": destiny_num,
            "tong_gia_tri": total,
            "la_master_number": destiny_num in MASTER_NUMBERS,
            "y_nghia": meaning,
        }
    except Exception as e:
        logger.error(f"Lỗi tính số sứ mệnh: {e}")
        return {"success": False, "error": str(e)}


def soul_urge(ho_ten: str) -> Dict[str, Any]:
    """Tính số linh hồn (Soul Urge/Heart's Desire Number) từ nguyên âm trong tên.

    Số linh hồn thể hiện khao khát nội tâm, động lực sâu thẳm và 
    những gì thực sự thúc đẩy bạn.

    Args:
        ho_ten: Họ tên đầy đủ (ví dụ: "Nguyễn Văn A")

    Returns:
        Dict chứa số linh hồn và ý nghĩa của nó.

    Examples:
        >>> soul_urge("Nguyen Van A")
        {'success': True, 'so_linh_hon': 3, 'y_nghia': {...}}
    """
    try:
        if not ho_ten or not ho_ten.strip():
            return {"success": False, "error": "Họ tên không được để trống"}

        total = _get_vowels_value(ho_ten)
        soul_num = _reduce_to_single(total, keep_master=True)
        meaning = _get_number_meaning(soul_num)

        # Get vowels used
        normalized = _normalize_name(ho_ten)
        vowels_used = [c for c in normalized if c in VOWELS]

        logger.info(f"Soul Urge: {ho_ten} -> {soul_num}")

        return {
            "success": True,
            "ho_ten": ho_ten,
            "nguyen_am": ''.join(vowels_used),
            "so_linh_hon": soul_num,
            "tong_gia_tri": total,
            "la_master_number": soul_num in MASTER_NUMBERS,
            "y_nghia": meaning,
        }
    except Exception as e:
        logger.error(f"Lỗi tính số linh hồn: {e}")
        return {"success": False, "error": str(e)}


def personality(ho_ten: str) -> Dict[str, Any]:
    """Tính số nhân cách (Personality Number) từ phụ âm trong tên.

    Số nhân cách thể hiện cách bạn thể hiện bản thân ra bên ngoài,
    ấn tượng đầu tiên mà người khác có về bạn.

    Args:
        ho_ten: Họ tên đầy đủ (ví dụ: "Nguyễn Văn A")

    Returns:
        Dict chứa số nhân cách và ý nghĩa của nó.

    Examples:
        >>> personality("Nguyen Van A")
        {'success': True, 'so_nhan_cach': 5, 'y_nghia': {...}}
    """
    try:
        if not ho_ten or not ho_ten.strip():
            return {"success": False, "error": "Họ tên không được để trống"}

        total = _get_consonants_value(ho_ten)
        personality_num = _reduce_to_single(total, keep_master=True)
        meaning = _get_number_meaning(personality_num)

        # Get consonants used
        normalized = _normalize_name(ho_ten)
        consonants_used = [c for c in normalized if c not in VOWELS]

        logger.info(f"Personality: {ho_ten} -> {personality_num}")

        return {
            "success": True,
            "ho_ten": ho_ten,
            "phu_am": ''.join(consonants_used),
            "so_nhan_cach": personality_num,
            "tong_gia_tri": total,
            "la_master_number": personality_num in MASTER_NUMBERS,
            "y_nghia": meaning,
        }
    except Exception as e:
        logger.error(f"Lỗi tính số nhân cách: {e}")
        return {"success": False, "error": str(e)}


def personal_year(ngay_sinh: int, thang_sinh: int, nam_xem: int = None) -> Dict[str, Any]:
    """Tính năm cá nhân (Personal Year Number).

    Năm cá nhân cho biết chủ đề và năng lượng chính của năm đó,
    giúp bạn biết nên tập trung vào điều gì.

    Args:
        ngay_sinh: Ngày sinh (1-31)
        thang_sinh: Tháng sinh (1-12)
        nam_xem: Năm cần xem (mặc định là năm hiện tại)

    Returns:
        Dict chứa số năm cá nhân và lời khuyên.

    Examples:
        >>> personal_year(15, 6, 2024)
        {'success': True, 'nam_ca_nhan': 7, 'chu_de': '...'}
    """
    try:
        if not (1 <= ngay_sinh <= 31) or not (1 <= thang_sinh <= 12):
            return {"success": False, "error": "Ngày hoặc tháng không hợp lệ"}

        if nam_xem is None:
            nam_xem = datetime.now().year

        # Personal year = day + month + year (all reduced and summed)
        total = ngay_sinh + thang_sinh + sum(int(d) for d in str(nam_xem))
        personal_year_num = _reduce_to_single(total, keep_master=False)  # Personal year doesn't keep master

        # Personal year themes
        year_themes = {
            1: {"chu_de": "Khởi đầu mới", "loi_khuyen": "Năm để bắt đầu dự án mới, thể hiện bản thân, độc lập"},
            2: {"chu_de": "Hợp tác & Kiên nhẫn", "loi_khuyen": "Năm để xây dựng mối quan hệ, hợp tác, kiên nhẫn chờ đợi"},
            3: {"chu_de": "Sáng tạo & Giao tiếp", "loi_khuyen": "Năm để thể hiện sáng tạo, mở rộng giao tiếp, vui vẻ"},
            4: {"chu_de": "Xây dựng nền tảng", "loi_khuyen": "Năm để làm việc chăm chỉ, xây dựng nền tảng vững chắc"},
            5: {"chu_de": "Thay đổi & Tự do", "loi_khuyen": "Năm của thay đổi, du lịch, trải nghiệm mới"},
            6: {"chu_de": "Gia đình & Trách nhiệm", "loi_khuyen": "Năm tập trung vào gia đình, trách nhiệm, yêu thương"},
            7: {"chu_de": "Tĩnh lặng & Phân tích", "loi_khuyen": "Năm để suy ngẫm, học hỏi, phát triển tâm linh"},
            8: {"chu_de": "Thành công & Quyền lực", "loi_khuyen": "Năm của thành tựu tài chính, sự nghiệp, quyền lực"},
            9: {"chu_de": "Kết thúc & Buông bỏ", "loi_khuyen": "Năm để hoàn thành, buông bỏ, chuẩn bị cho chu kỳ mới"},
        }

        theme = year_themes.get(personal_year_num, {})

        logger.info(f"Personal Year: {ngay_sinh}/{thang_sinh} in {nam_xem} -> {personal_year_num}")

        return {
            "success": True,
            "ngay_sinh": f"{ngay_sinh}/{thang_sinh}",
            "nam_xem": nam_xem,
            "nam_ca_nhan": personal_year_num,
            "chu_de": theme.get("chu_de", ""),
            "loi_khuyen": theme.get("loi_khuyen", ""),
        }
    except Exception as e:
        logger.error(f"Lỗi tính năm cá nhân: {e}")
        return {"success": False, "error": str(e)}


def full_profile(ho_ten: str, ngay_sinh: int, thang_sinh: int, nam_sinh: int) -> Dict[str, Any]:
    """Tổng hợp đầy đủ hồ sơ thần số học.

    Tính toán tất cả các con số quan trọng và cung cấp phân tích
    toàn diện về con người dựa trên họ tên và ngày sinh.

    Args:
        ho_ten: Họ tên đầy đủ (ví dụ: "Nguyễn Văn A")
        ngay_sinh: Ngày sinh (1-31)
        thang_sinh: Tháng sinh (1-12)
        nam_sinh: Năm sinh (ví dụ: 1990)

    Returns:
        Dict chứa tất cả các con số và phân tích tổng hợp.

    Examples:
        >>> full_profile("Nguyen Van A", 15, 6, 1990)
        {'success': True, 'profile': {...}}
    """
    try:
        # Calculate all numbers
        life_path_result = life_path(ngay_sinh, thang_sinh, nam_sinh)
        destiny_result = destiny(ho_ten)
        soul_urge_result = soul_urge(ho_ten)
        personality_result = personality(ho_ten)
        personal_year_result = personal_year(ngay_sinh, thang_sinh)

        # Check for errors
        for result in [life_path_result, destiny_result, soul_urge_result, 
                       personality_result, personal_year_result]:
            if not result.get("success"):
                return result

        # Birthday number (just the day reduced)
        birthday_num = _reduce_to_single(ngay_sinh, keep_master=False)

        logger.info(f"Full Profile: {ho_ten}, {ngay_sinh}/{thang_sinh}/{nam_sinh}")

        return {
            "success": True,
            "ho_ten": ho_ten,
            "ngay_sinh": f"{ngay_sinh}/{thang_sinh}/{nam_sinh}",
            "profile": {
                "so_chu_dao": {
                    "so": life_path_result["so_chu_dao"],
                    "ten": life_path_result["y_nghia"].get("name", ""),
                    "la_master": life_path_result["la_master_number"],
                },
                "so_su_menh": {
                    "so": destiny_result["so_su_menh"],
                    "ten": destiny_result["y_nghia"].get("name", ""),
                    "la_master": destiny_result["la_master_number"],
                },
                "so_linh_hon": {
                    "so": soul_urge_result["so_linh_hon"],
                    "ten": soul_urge_result["y_nghia"].get("name", ""),
                    "la_master": soul_urge_result["la_master_number"],
                },
                "so_nhan_cach": {
                    "so": personality_result["so_nhan_cach"],
                    "ten": personality_result["y_nghia"].get("name", ""),
                    "la_master": personality_result["la_master_number"],
                },
                "so_ngay_sinh": birthday_num,
                "nam_ca_nhan": {
                    "so": personal_year_result["nam_ca_nhan"],
                    "chu_de": personal_year_result["chu_de"],
                },
            },
            "tom_tat": (
                f"Với số chủ đạo {life_path_result['so_chu_dao']} ({life_path_result['y_nghia'].get('name', '')}), "
                f"bạn có con đường sống thiên về {', '.join(life_path_result['y_nghia'].get('keywords', [])[:2])}. "
                f"Số sứ mệnh {destiny_result['so_su_menh']} cho thấy tài năng tiềm ẩn của bạn. "
                f"Năm {datetime.now().year} là năm cá nhân số {personal_year_result['nam_ca_nhan']} - {personal_year_result['chu_de']}."
            ),
        }
    except Exception as e:
        logger.error(f"Lỗi tính full profile: {e}")
        return {"success": False, "error": str(e)}
