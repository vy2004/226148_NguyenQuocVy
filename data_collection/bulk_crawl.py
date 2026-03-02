"""
Crawl hàng loạt tài liệu lịch sử Việt Nam từ Wikipedia.
Chạy 1 lần để nạp kiến thức nền cho chatbot.
"""
import os
import sys
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "data_collection"))
sys.path.insert(0, os.path.join(ROOT_DIR, "data_processing"))

from wiki_crawler import search_wikipedia, save_wiki_to_raw
from source_manager import is_already_crawled, mark_as_crawled
from dynamic_indexing import add_new_documents

# =====================================================
# DANH SÁCH CHỦ ĐỀ LỊCH SỬ VIỆT NAM CẦN CRAWL
# =====================================================

TOPICS = {
    # ============ THỜI KỲ CỔ ĐẠI ============
    "Thời kỳ cổ đại": [
        "Văn Lang", "Âu Lạc", "Hùng Vương", "An Dương Vương", "Thục Phán",
        "Nỏ thần liên châu", "Trống đồng Đông Sơn", "Văn hóa Đông Sơn",
        "Văn hóa Sa Huỳnh", "Thánh Gióng", "Sơn Tinh Thủy Tinh",
        "Lạc Long Quân Âu Cơ", "Văn hóa Phùng Nguyên", "Văn hóa Đồng Đậu",
        "Văn hóa Gò Mun", "Văn hóa Óc Eo", "Chăm Pa", "Phù Nam",
    ],

    # ============ BẮC THUỘC VÀ CHỐNG BẮC THUỘC ============
    "Bắc thuộc": [
        "Bắc thuộc lần thứ nhất", "Bắc thuộc lần thứ hai",
        "Bắc thuộc lần thứ ba", "Bắc thuộc lần thứ tư",
        "Hai Bà Trưng", "Khởi nghĩa Hai Bà Trưng",
        "Bà Triệu", "Khởi nghĩa Bà Triệu",
        "Lý Bí", "Nhà Tiền Lý", "Triệu Quang Phục",
        "Mai Thúc Loan", "Phùng Hưng", "Khúc Thừa Dụ",
        "Dương Đình Nghệ", "Ngô Quyền", "Trận Bạch Đằng năm 938",
    ],

    # ============ THỜI KỲ PHONG KIẾN ĐỘC LẬP ============
    "Phong kiến độc lập": [
        "Nhà Ngô", "Loạn 12 sứ quân", "Đinh Bộ Lĩnh", "Nhà Đinh",
        "Lê Hoàn", "Nhà Tiền Lê", "Trận Bạch Đằng năm 981",
        "Nhà Lý", "Lý Thái Tổ", "Lý Thường Kiệt",
        "Trận sông Như Nguyệt", "Nhà Trần", "Trần Thái Tông",
        "Trần Hưng Đạo", "Trần Quốc Tuấn",
        "Chiến tranh Nguyên Mông – Đại Việt",
        "Trận Bạch Đằng năm 1288", "Hịch tướng sĩ",
        "Nhà Hồ", "Hồ Quý Ly",
    ],

    # ============ THỜI KỲ LÊ - NGUYỄN ============
    "Thời Lê - Nguyễn": [
        "Khởi nghĩa Lam Sơn", "Lê Lợi", "Lê Thái Tổ", "Nguyễn Trãi",
        "Bình Ngô đại cáo", "Nhà Hậu Lê", "Lê Thánh Tông",
        "Nhà Mạc", "Trịnh Nguyễn phân tranh", "Chúa Trịnh", "Chúa Nguyễn",
        "Phong trào Tây Sơn", "Nguyễn Huệ", "Quang Trung",
        "Trận Rạch Gầm – Xoài Mút", "Trận Ngọc Hồi – Đống Đa",
        "Nhà Nguyễn", "Gia Long", "Minh Mạng", "Tự Đức",
    ],

    # ============ CHỐNG PHÁP ============
    "Kháng chiến chống Pháp": [
        "Pháp xâm lược Việt Nam", "Trận Đà Nẵng 1858",
        "Hòa ước Nhâm Tuất", "Hòa ước Giáp Tuất", "Hòa ước Pa-tơ-nốt",
        "Phong trào Cần Vương", "Tôn Thất Thuyết", "Vua Hàm Nghi",
        "Khởi nghĩa Hương Khê", "Phan Đình Phùng",
        "Khởi nghĩa Yên Thế", "Hoàng Hoa Thám",
        "Đông Kinh Nghĩa Thục", "Phan Bội Châu", "Phan Châu Trinh",
        "Phong trào Đông Du", "Đảng Cộng sản Việt Nam",
        "Nguyễn Ái Quốc", "Xô viết Nghệ Tĩnh", "Mặt trận Việt Minh",
        "Cách mạng Tháng Tám", "Tuyên ngôn Độc lập Việt Nam",
        "Chiến tranh Đông Dương", "Chiến dịch Việt Bắc",
        "Chiến dịch Biên giới thu đông 1950",
        "Trận Điện Biên Phủ", "Võ Nguyên Giáp", "Hiệp định Genève 1954",
    ],

    # ============ KHÁNG CHIẾN CHỐNG MỸ ============
    "Kháng chiến chống Mỹ": [
        "Chiến tranh Việt Nam", "Ngô Đình Diệm", "Việt Nam Cộng hòa",
        "Mặt trận Dân tộc Giải phóng miền Nam Việt Nam",
        "Chiến tranh du kích miền Nam Việt Nam",
        "Phong trào Đồng khởi", "Chiến thắng Ấp Bắc",
        "Sự kiện Vịnh Bắc Bộ", "Chiến dịch Pleiku",
        "Đường Trường Sơn", "Đường mòn Hồ Chí Minh",
        "Chất độc da cam", "Tổng tiến công Tết Mậu Thân 1968",
        "Thảm sát Mỹ Lai", "Chiến dịch Linebacker II",
        "Hiệp định Paris 1973", "Chiến dịch Hồ Chí Minh",
        "Sự kiện 30 tháng 4 năm 1975", "Thống nhất Việt Nam",
        "Lê Duẩn", "Phạm Văn Đồng", "Trường Chinh", "Nguyễn Văn Thiệu",
    ],

    # ============ SAU 1975 ============
    "Sau thống nhất": [
        "Chiến tranh biên giới Việt Nam – Campuchia",
        "Chiến tranh biên giới Việt – Trung 1979",
        "Đổi mới (Việt Nam)", "Kinh tế Việt Nam",
        "Việt Nam gia nhập ASEAN", "Việt Nam gia nhập WTO",
        "Nguyễn Văn Linh", "Đỗ Mười", "Võ Văn Kiệt",
        "Phan Văn Khải", "Nguyễn Tấn Dũng",
    ],

    # ============ NHÂN VẬT LỊCH SỬ ============
    "Nhân vật lịch sử": [
        "Hồ Chí Minh", "Võ Nguyên Giáp", "Trần Hưng Đạo",
        "Lê Lợi", "Nguyễn Huệ", "Nguyễn Trãi",
        "Lý Thường Kiệt", "Ngô Quyền", "Hai Bà Trưng", "Bà Triệu",
        "Đinh Bộ Lĩnh", "Lê Thánh Tông", "Phan Bội Châu",
        "Phan Châu Trinh", "Nguyễn Thị Minh Khai",
        "Tôn Đức Thắng", "Phạm Ngọc Thạch", "Nguyễn Văn Trỗi",
    ],

    # ============ ĐỊA DANH LỊCH SỬ ============
    "Địa danh lịch sử": [
        "Hoàng thành Thăng Long", "Cố đô Huế", "Địa đạo Củ Chi",
        "Nhà tù Côn Đảo", "Nhà tù Hỏa Lò", "Thành nhà Hồ",
        "Thánh địa Mỹ Sơn", "Khu di tích Pác Bó",
        "Chiến khu Việt Bắc", "Dinh Độc Lập",
    ],

    # ============ [MỚI] DANH NHÂN BỔ SUNG ============
    "Danh nhân bổ sung": [
        "Lý Thái Tổ", "Lý Nhân Tông", "Trần Nhân Tông", "Trần Anh Tông",
        "Lê Lai", "Nguyễn Chích", "Lê Văn Hưu", "Chu Văn An",
        "Nguyễn Bỉnh Khiêm", "Lê Quý Đôn", "Nguyễn Du",
        "Hồ Xuân Hương", "Đoàn Thị Điểm", "Nguyễn Đình Chiểu",
        "Trương Định", "Nguyễn Tri Phương", "Hoàng Diệu",
        "Nguyễn Thái Học", "Lý Tự Trọng", "Ngô Gia Tự",
        "Trần Phú", "Lê Hồng Phong", "Hà Huy Tập",
        "Nguyễn Văn Cừ", "Hoàng Văn Thụ", "Kim Đồng",
        "Võ Thị Sáu", "Nguyễn Thị Lý",
    ],

    # ============ [MỚI] VĂN HÓA - NGHỆ THUẬT ============
    "Văn hóa Việt Nam": [
        "Văn hóa Việt Nam", "Lịch sử văn học Việt Nam",
        "Chữ Nôm", "Chữ Quốc ngữ", "Truyện Kiều",
        "Thơ ca dân gian Việt Nam", "Tuồng (nghệ thuật)",
        "Chèo (nghệ thuật)", "Múa rối nước",
        "Nhã nhạc cung đình Huế", "Quan họ Bắc Ninh",
        "Đờn ca tài tử Nam Bộ", "Ca trù", "Hát xoan",
        "Áo dài", "Ẩm thực Việt Nam", "Tết Nguyên Đán",
        "Lễ hội Đền Hùng", "Hội Gióng",
        "Phở", "Bánh chưng",
        "Làng nghề truyền thống Việt Nam", "Gốm Bát Tràng",
        "Lụa Vạn Phúc", "Tranh Đông Hồ",
    ],

    # ============ [MỚI] TÔN GIÁO - TƯ TƯỞNG ============
    "Tôn giáo và tư tưởng": [
        "Phật giáo tại Việt Nam", "Thiền phái Trúc Lâm",
        "Trần Nhân Tông", "Khổng giáo tại Việt Nam",
        "Đạo giáo tại Việt Nam", "Công giáo tại Việt Nam",
        "Cao Đài", "Hòa Hảo",
        "Tín ngưỡng thờ Mẫu của người Việt",
        "Thờ cúng tổ tiên", "Đạo Mẫu",
        "Tứ bất tử (Việt Nam)", "Văn Miếu – Quốc Tử Giám",
        "Giáo dục thời phong kiến Việt Nam",
        "Thi cử Nho học Việt Nam",
    ],

    # ============ [MỚI] KIẾN TRÚC - DI SẢN ============
    "Kiến trúc và di sản": [
        "Kiến trúc Việt Nam", "Chùa Một Cột", "Chùa Trấn Quốc",
        "Chùa Hương", "Chùa Yên Tử", "Chùa Thiên Mụ",
        "Đình làng Việt Nam", "Phố cổ Hội An",
        "Vịnh Hạ Long", "Vườn quốc gia Phong Nha - Kẻ Bàng",
        "Cố đô Hoa Lư", "Thành cổ Quảng Trị",
        "Lăng Tự Đức", "Lăng Khải Định", "Cầu Trường Tiền",
        "Tháp Chăm", "Tháp Bà Ponagar",
        "Di sản thế giới tại Việt Nam",
    ],

    # ============ [MỚI] ĐỊA LÝ - VÙNG MIỀN ============
    "Địa lý và vùng miền": [
        "Đồng bằng sông Hồng", "Đồng bằng sông Cửu Long",
        "Tây Nguyên", "Duyên hải Nam Trung Bộ",
        "Đông Bắc (Việt Nam)", "Tây Bắc (Việt Nam)",
        "Sông Hồng", "Sông Mê Kông", "Sông Bạch Đằng",
        "Hà Nội", "Thành phố Hồ Chí Minh", "Huế",
        "Đà Nẵng", "Hải Phòng", "Cần Thơ",
        "Biển Đông", "Quần đảo Hoàng Sa", "Quần đảo Trường Sa",
    ],

    # ============ [MỚI] KINH TẾ - XÃ HỘI ============
    "Kinh tế xã hội": [
        "Nông nghiệp Việt Nam", "Làng xã Việt Nam",
        "Chế độ phong kiến Việt Nam", "Chế độ ruộng đất Việt Nam",
        "Thương mại Việt Nam thời phong kiến",
        "Con đường tơ lụa trên biển", "Hội An thương cảng",
        "Hệ thống thuỷ lợi Việt Nam",
        "Nghệ thuật quân sự Việt Nam",
        "Binh thư yếu lược", "Hịch tướng sĩ",
    ],

    # ============ [MỚI] TRIỀU ĐẠI CHI TIẾT ============
    "Triều đại chi tiết": [
        "Nhà Lý", "Nhà Trần", "Nhà Hồ", "Nhà Hậu Lê",
        "Nhà Mạc", "Nhà Tây Sơn", "Nhà Nguyễn",
        "Lê Thái Tông", "Lê Nhân Tông",
        "Lê Hiến Tông", "Lê Uy Mục", "Lê Chiêu Tông",
        "Thiệu Trị", "Hàm Nghi", "Thành Thái",
        "Duy Tân", "Khải Định", "Bảo Đại",
    ],

    # ============ [MỚI] LỊCH SỬ ĐẢNG VÀ CÁCH MẠNG ============
    "Lịch sử Đảng và cách mạng": [
        "Hội Việt Nam Cách mạng Thanh niên",
        "Việt Nam Quốc dân Đảng", "Khởi nghĩa Yên Bái",
        "Xô viết Nghệ Tĩnh", "Nam Kỳ khởi nghĩa",
        "Khởi nghĩa Bắc Sơn", "Khởi nghĩa Ba Tơ",
        "Tổng khởi nghĩa tháng Tám",
        "Quân đội nhân dân Việt Nam",
        "Công an nhân dân Việt Nam",
        "Mặt trận Tổ quốc Việt Nam",
        "Hội Liên hiệp Phụ nữ Việt Nam",
        "Đoàn Thanh niên Cộng sản Hồ Chí Minh",
    ],

    # ============ [MỚI] CÁC DÂN TỘC VIỆT NAM ============
    "Các dân tộc Việt Nam": [
        "Dân tộc Kinh", "Dân tộc Tày",
        "Dân tộc Thái (Việt Nam)", "Dân tộc Mường",
        "Dân tộc Khmer (Việt Nam)", "Dân tộc Hoa (Việt Nam)",
        "Dân tộc Nùng", "Dân tộc H'Mông", "Dân tộc Dao",
        "Dân tộc Gia Rai", "Dân tộc Ê Đê", "Dân tộc Ba Na",
        "Người Chăm", "54 dân tộc Việt Nam",
    ],

    # ============ [MỚI] TRẬN ĐÁNH CHI TIẾT - KHÁNG CHIẾN CHỐNG PHÁP ============
    "Trận đánh chống Pháp": [
        "Trận Đà Nẵng (1858)", "Trận Cầu Giấy (1873)",
        "Trận Cầu Giấy (1883)", "Trận Phai Khắt",
        "Trận Nà Ngần", "Chiến dịch Hòa Bình",
        "Chiến dịch Tây Bắc", "Chiến dịch Thượng Lào",
        "Chiến dịch Trung Lào", "Chiến dịch Hạ Lào",
        "Chiến dịch Đông Xuân 1953-1954",
        "Trận Nghĩa Lộ", "Chiến dịch Lý Thường Kiệt",
        "Trận Tu Vũ", "Chiến dịch Trần Hưng Đạo",
        "Chiến dịch Quang Trung", "Chiến dịch Hoàng Hoa Thám",
        "Trận Đông Khê", "Chiến dịch Atlante",
    ],

    # ============ [MỚI] TRẬN ĐÁNH CHI TIẾT - KHÁNG CHIẾN CHỐNG MỸ ============
    "Trận đánh chống Mỹ chi tiết": [
        "Chiến dịch Tây Nguyên", "Chiến dịch Huế – Đà Nẵng",
        "Chiến dịch Trị Thiên", "Chiến dịch Khe Sanh",
        "Trận Khe Sanh", "Trận Đắk Tô – Tân Cảnh",
        "Chiến dịch Nguyễn Huệ", "Chiến dịch Junction City",
        "Chiến dịch Cedar Falls", "Chiến dịch Lam Sơn 719",
        "Chiến dịch Xuân Hè 1972", "Trận An Lộc",
        "Trận Kontum (1972)", "Chiến dịch phòng không Hà Nội",
        "Chiến dịch Đường 9 – Nam Lào",
        "Chiến dịch Đường 14 – Phước Long",
        "Trận Buôn Ma Thuột", "Trận Xuân Lộc",
        "Chiến dịch Nông Sơn – Đà Nẵng",
        "Trận Quảng Trị (1972)", "Chiến dịch Phước Bình",
    ],

    # ============ [MỚI] THÀNH CỔ VÀ TRẬN ĐÁNH TỈNH THÀNH ============
    "Trận đánh tỉnh thành": [
        "Thành cổ Quảng Trị", "Trận Huế (1968)",
        "Trận Sài Gòn (1968)", "Trận Đà Lạt (1968)",
        "Trận Bình Long", "Trận Long Khánh",
        "Trận Phước Long (1975)", "Trận Phan Rang (1975)",
        "Trận Nha Trang (1975)", "Trận Quy Nhơn (1975)",
        "Chiến dịch giải phóng Đà Nẵng",
        "Chiến dịch giải phóng Huế (1975)",
        "Giải phóng Sài Gòn", "Trận cầu Rạch Chiếc",
        "Trận sân bay Tân Sơn Nhất",
        "Trận Dinh Độc Lập 30 tháng 4",
    ],

    # ============ [MỚI] CHIẾN TRANH BIÊN GIỚI TÂY NAM (POLPOT) ============
    "Chiến tranh biên giới Tây Nam": [
        "Khmer Đỏ", "Pol Pot", "Chế độ diệt chủng Khmer Đỏ",
        "Thảm sát Ba Chúc", "Tỉnh An Giang",
        "Chiến dịch phản công biên giới Tây Nam",
        "Chiến dịch giải phóng Phnom Penh",
        "Quân tình nguyện Việt Nam tại Campuchia",
        "Trận Svay Riêng", "Hội nghị Phnom Penh",
        "Mặt trận Đoàn kết Cứu quốc Campuchia",
        "Ieng Sary", "Ta Mok", "Nuon Chea",
        "Cánh đồng chết", "Tòa án xét xử tội ác Khmer Đỏ",
        "Tỉnh Tây Ninh", "Tỉnh Kiên Giang",
        "Hà Tiên", "Chiến tranh Campuchia–Việt Nam",
    ],

    # ============ [MỚI] CHIẾN TRANH BIÊN GIỚI PHÍA BẮC CHI TIẾT ============
    "Chiến tranh biên giới phía Bắc chi tiết": [
        "Trận Lạng Sơn (1979)", "Trận Cao Bằng (1979)",
        "Trận Lào Cai (1979)", "Trận Hà Giang (1979)",
        "Chiến dịch phòng thủ Lạng Sơn",
        "Trận Đồng Đăng", "Trận Vị Xuyên",
        "Mặt trận Vị Xuyên", "Cao điểm 1509",
        "Chiến tranh biên giới 1984-1989",
        "Tỉnh Quảng Ninh biên giới",
        "Tỉnh Lai Châu biên giới",
    ],

    # ============ [MỚI] KHÔNG QUÂN - PHÒNG KHÔNG ============
    "Không quân và phòng không": [
        "Phòng không Việt Nam", "Tên lửa SAM-2",
        "Boeing B-52 Stratofortress", "Trận Hà Nội – Hải Phòng 1972",
        "Phi công Việt Nam", "Nguyễn Văn Bảy",
        "Phạm Tuân", "Phi công ace Việt Nam",
        "MiG-21 Việt Nam", "Không quân nhân dân Việt Nam",
        "Hải quân nhân dân Việt Nam",
        "Chiến dịch Rolling Thunder",
        "Chiến dịch Arc Light", "Chiến dịch Flaming Dart",
        "Chiến dịch Menu", "Chiến dịch Barrel Roll",
        "Phòng tuyến sông Bến Hải",
        "Vĩ tuyến 17", "Khu phi quân sự vĩ tuyến 17",
    ],

    # ============ [MỚI] CÁC TỈNH THÀNH LỊCH SỬ ============
    "Tỉnh thành lịch sử": [
        "Quảng Trị", "Thừa Thiên Huế", "Quảng Nam",
        "Quảng Ngãi", "Bình Định", "Phú Yên",
        "Khánh Hòa", "Nghệ An", "Hà Tĩnh",
        "Thanh Hóa", "Thái Nguyên", "Bắc Giang",
        "Lạng Sơn", "Cao Bằng", "Hà Giang",
        "Tây Ninh", "Bình Phước", "Đồng Nai",
        "Bà Rịa – Vũng Tàu", "Long An", "Tiền Giang",
        "Bến Tre", "An Giang", "Kiên Giang",
        "Đắk Lắk", "Gia Lai", "Kon Tum",
        "Lâm Đồng", "Sơn La", "Điện Biên",
    ],

    # ============ [MỚI] VŨ KHÍ - QUÂN SỰ ============
    "Vũ khí và quân sự Việt Nam": [
        "AK-47", "RPG-7", "Tên lửa đất đối không",
        "Xe tăng T-54", "Pháo phòng không 37mm",
        "Súng trường M16", "Trực thăng UH-1 Iroquois",
        "Napalm", "Bom bi", "Mìn Claymore",
        "Đặc công Việt Nam", "Bộ đội đặc công",
        "Lực lượng đặc biệt Việt Nam",
        "Biệt động Sài Gòn", "Dân quân tự vệ Việt Nam",
        "Thanh niên xung phong",
    ],

    # ============ [MỚI] NGOẠI GIAO - QUAN HỆ QUỐC TẾ ============
    "Ngoại giao Việt Nam": [
        "Quan hệ Việt Nam – Trung Quốc",
        "Quan hệ Việt Nam – Hoa Kỳ",
        "Quan hệ Việt Nam – Liên Xô",
        "Quan hệ Việt Nam – Pháp",
        "Quan hệ Việt Nam – Nhật Bản",
        "Quan hệ Việt Nam – Hàn Quốc",
        "ASEAN", "Liên Hợp Quốc",
        "Tổ chức Thương mại Thế giới",
        "Hiệp ước Hữu nghị và Hợp tác Việt Nam – Liên Xô",
        "Viện trợ quân sự cho Việt Nam Dân chủ Cộng hòa",
        "Phong trào phản chiến tại Hoa Kỳ",
    ],

    # ============ [MỚI] GIÁO DỤC - Y TẾ LỊCH SỬ ============
    "Giáo dục và y tế": [
        "Giáo dục Việt Nam", "Lịch sử giáo dục Việt Nam",
        "Đại học Quốc gia Hà Nội", "Đại học Y Hà Nội",
        "Trường Đông Kinh Nghĩa Thục", "Trường Quốc học Huế",
        "Bình dân học vụ", "Xóa mù chữ tại Việt Nam",
        "Alexandre de Rhodes", "Đại học Đông Dương",
        "Viện Pasteur Sài Gòn", "Y học cổ truyền Việt Nam",
        "Hải Thượng Lãn Ông", "Tuệ Tĩnh",
    ],

    # ============ [MỚI] DI TÍCH QUỐC GIA ĐẶC BIỆT ============
    "Di tích quốc gia": [
        "Đền Hùng", "Văn Miếu – Quốc Tử Giám",
        "Lăng Chủ tịch Hồ Chí Minh", "Bảo tàng Lịch sử Quốc gia",
        "Bảo tàng Chứng tích Chiến tranh",
        "Bảo tàng Hồ Chí Minh", "Đền Trần",
        "Đền Kiếp Bạc", "Đền Gióng", "Đền Cờn",
        "Thành Cổ Loa", "Đền Đô", "Chùa Bút Tháp",
        "Phủ Tây Hồ", "Chùa Keo", "Chùa Tây Phương",
        "Đình Bảng", "Đình Tây Đằng",
        "Khu di tích Kim Liên", "Khu di tích ATK Định Hóa",
    ],

    # ============ [MỚI] CHIẾN DỊCH QUÂN SỰ THỜI PHONG KIẾN ============
    "Chiến dịch phong kiến": [
        "Trận Như Nguyệt", "Trận Chi Lăng – Xương Giang",
        "Trận Tốt Động – Chúc Động", "Trận Đống Đa",
        "Trận cửa Hàm Tử", "Trận Chương Dương",
        "Trận Vân Đồn", "Trận Tây Kết",
        "Kế hoạch vườn không nhà trống",
        "Chiến thuật du kích thời Trần",
        "Binh pháp Trần Hưng Đạo",
        "Trận Bồ Cô", "Trận Khôi Huyện",
    ],

    # ============ [MỚI] KINH TẾ HIỆN ĐẠI ============
    "Kinh tế hiện đại": [
        "Kinh tế thị trường định hướng xã hội chủ nghĩa",
        "Công nghiệp hóa Việt Nam", "FDI tại Việt Nam",
        "Dầu khí Việt Nam", "Nông nghiệp Việt Nam",
        "Xuất khẩu gạo Việt Nam", "Cà phê Việt Nam",
        "Du lịch Việt Nam", "Hàng không Việt Nam",
        "Vietnam Airlines", "Viettel",
        "Đường sắt Việt Nam", "Quốc lộ 1",
        "Đường cao tốc Bắc – Nam",
    ],
}



def crawl_all():
    """Crawl tất cả chủ đề lịch sử."""
    print("=" * 60)
    print("  CRAWL DỮ LIỆU LỊCH SỬ VIỆT NAM TỪ WIKIPEDIA")
    print("  (Lưu vào ChromaDB)")
    print("=" * 60)

    total_articles = 0
    total_chunks = 0
    skipped = 0

    for i, topic in enumerate(TOPICS):
        print(f"\n[{i+1}/{len(TOPICS)}] 📌 Chủ đề: {topic}")

        # Kiểm tra đã crawl chưa
        if is_already_crawled(topic):
            print(f"  ⏭️ Đã crawl trước đó, bỏ qua.")
            skipped += 1
            continue

        # Crawl từ Wikipedia
        articles = search_wikipedia(topic, max_results=2)

        if not articles:
            print(f"  ❌ Không tìm thấy bài viết nào.")
            continue

        # Lưu vào data/raw/
        save_wiki_to_raw(articles)

        # Chuyển đổi thành documents và thêm vào ChromaDB
        documents = []
        for article in articles:
            documents.append({
                "content": article["content"],
                "metadata": {
                    "source": "wikipedia",
                    "title": article["title"],
                    "url": article.get("url", ""),
                    "topic": topic
                }
            })

        chunks_added = add_new_documents(documents)
        total_articles += len(articles)
        total_chunks += chunks_added

        # Đánh dấu đã crawl
        mark_as_crawled(topic)

        # Nghỉ giữa các request
        time.sleep(1)

    print("\n" + "=" * 60)
    print(f"✅ HOÀN TẤT CRAWL!")
    print(f"   📄 Bài viết mới: {total_articles}")
    print(f"   📦 Chunks mới: {total_chunks}")
    print(f"   ⏭️ Bỏ qua (đã crawl): {skipped}")
    print("=" * 60)


if __name__ == "__main__":
    crawl_all()