"""
Crawl hàng loạt tài liệu lịch sử Việt Nam từ Wikipedia.
Chạy 1 lần để nạp kiến thức nền cho chatbot.
"""
import sys
import os
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "data_collection"))
sys.path.insert(0, os.path.join(ROOT_DIR, "data_processing"))
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

from wiki_crawler import search_wikipedia
from source_manager import is_already_crawled, mark_as_crawled
from dynamic_indexing import add_new_documents

# =====================================================
# DANH SÁCH CHỦ ĐỀ LỊCH SỬ VIỆT NAM CẦN CRAWL
# =====================================================

TOPICS = {
    # ============ THỜI KỲ CỔ ĐẠI ============
    "Thời kỳ cổ đại": [
        "Văn Lang",
        "Âu Lạc",
        "Hùng Vương",
        "An Dương Vương",
        "Thục Phán",
        "Nỏ thần liên châu",
        "Trống đồng Đông Sơn",
        "Văn hóa Đông Sơn",
        "Văn hóa Sa Huỳnh",
        "Thánh Gióng",
        "Sơn Tinh Thủy Tinh",
        "Lạc Long Quân Âu Cơ",
    ],

    # ============ BẮC THUỘC VÀ CHỐNG BẮC THUỘC ============
    "Bắc thuộc": [
        "Bắc thuộc lần thứ nhất",
        "Bắc thuộc lần thứ hai",
        "Bắc thuộc lần thứ ba",
        "Bắc thuộc lần thứ tư",
        "Hai Bà Trưng",
        "Khởi nghĩa Hai Bà Trưng",
        "Bà Triệu",
        "Khởi nghĩa Bà Triệu",
        "Lý Bí",
        "Nhà Tiền Lý",
        "Triệu Quang Phục",
        "Mai Thúc Loan",
        "Phùng Hưng",
        "Khúc Thừa Dụ",
        "Dương Đình Nghệ",
        "Ngô Quyền",
        "Trận Bạch Đằng năm 938",
    ],

    # ============ THỜI KỲ PHONG KIẾN ĐỘC LẬP ============
    "Phong kiến độc lập": [
        "Nhà Ngô",
        "Loạn 12 sứ quân",
        "Đinh Bộ Lĩnh",
        "Nhà Đinh",
        "Lê Hoàn",
        "Nhà Tiền Lê",
        "Trận Bạch Đằng năm 981",
        "Nhà Lý",
        "Lý Thái Tổ",
        "Lý Thường Kiệt",
        "Trận sông Như Nguyệt",
        "Nhà Trần",
        "Trần Thái Tông",
        "Trần Hưng Đạo",
        "Trần Quốc Tuấn",
        "Chiến tranh Nguyên Mông – Đại Việt",
        "Trận Bạch Đằng năm 1288",
        "Hịch tướng sĩ",
        "Nhà Hồ",
        "Hồ Quý Ly",
    ],

    # ============ THỜI KỲ LÊ - NGUYỄN ============
    "Thời Lê - Nguyễn": [
        "Khởi nghĩa Lam Sơn",
        "Lê Lợi",
        "Lê Thái Tổ",
        "Nguyễn Trãi",
        "Bình Ngô đại cáo",
        "Nhà Hậu Lê",
        "Lê Thánh Tông",
        "Nhà Mạc",
        "Trịnh Nguyễn phân tranh",
        "Chúa Trịnh",
        "Chúa Nguyễn",
        "Phong trào Tây Sơn",
        "Nguyễn Huệ",
        "Quang Trung",
        "Trận Rạch Gầm – Xoài Mút",
        "Trận Ngọc Hồi – Đống Đa",
        "Nhà Nguyễn",
        "Gia Long",
        "Minh Mạng",
        "Tự Đức",
    ],

    # ============ CHỐNG PHÁP ============
    "Kháng chiến chống Pháp": [
        "Pháp xâm lược Việt Nam",
        "Trận Đà Nẵng 1858",
        "Hòa ước Nhâm Tuất",
        "Hòa ước Giáp Tuất",
        "Hòa ước Pa-tơ-nốt",
        "Phong trào Cần Vương",
        "Tôn Thất Thuyết",
        "Vua Hàm Nghi",
        "Khởi nghĩa Hương Khê",
        "Phan Đình Phùng",
        "Khởi nghĩa Yên Thế",
        "Hoàng Hoa Thám",
        "Đông Kinh Nghĩa Thục",
        "Phan Bội Châu",
        "Phan Châu Trinh",
        "Phong trào Đông Du",
        "Đảng Cộng sản Việt Nam",
        "Nguyễn Ái Quốc",
        "Xô viết Nghệ Tĩnh",
        "Mặt trận Việt Minh",
        "Cách mạng Tháng Tám",
        "Tuyên ngôn Độc lập Việt Nam",
        "Chiến tranh Đông Dương",
        "Chiến dịch Việt Bắc",
        "Chiến dịch Biên giới thu đông 1950",
        "Trận Điện Biên Phủ",
        "Võ Nguyên Giáp",
        "Hiệp định Genève 1954",
    ],

    # ============ KHÁNG CHIẾN CHỐNG MỸ ============
    "Kháng chiến chống Mỹ": [
        "Chiến tranh Việt Nam",
        "Ngô Đình Diệm",
        "Việt Nam Cộng hòa",
        "Mặt trận Dân tộc Giải phóng miền Nam Việt Nam",
        "Chiến tranh du kích miền Nam Việt Nam",
        "Phong trào Đồng khởi",
        "Chiến thắng Ấp Bắc",
        "Sự kiện Vịnh Bắc Bộ",
        "Chiến dịch Pleiku",
        "Đường Trường Sơn",
        "Đường mòn Hồ Chí Minh",
        "Chiến tranh hóa học Việt Nam",
        "Chất độc da cam",
        "Tổng tiến công Tết Mậu Thân 1968",
        "Thảm sát Mỹ Lai",
        "Chiến dịch Linebacker II",
        "Trận Điện Biên Phủ trên không",
        "Hiệp định Paris 1973",
        "Chiến dịch Hồ Chí Minh",
        "Sự kiện 30 tháng 4 năm 1975",
        "Thống nhất Việt Nam",
        "Lê Duẩn",
        "Phạm Văn Đồng",
        "Trường Chinh",
        "Nguyễn Văn Thiệu",
    ],

    # ============ SAU 1975 ============
    "Sau thống nhất": [
        "Chiến tranh biên giới Việt Nam – Campuchia",
        "Chiến tranh biên giới Việt – Trung 1979",
        "Đổi mới (Việt Nam)",
        "Kinh tế Việt Nam",
        "Việt Nam gia nhập ASEAN",
        "Việt Nam gia nhập WTO",
    ],

    # ============ NHÂN VẬT LỊCH SỬ QUAN TRỌNG ============
    "Nhân vật lịch sử": [
        "Hồ Chí Minh",
        "Võ Nguyên Giáp",
        "Trần Hưng Đạo",
        "Lê Lợi",
        "Nguyễn Huệ",
        "Nguyễn Trãi",
        "Lý Thường Kiệt",
        "Ngô Quyền",
        "Hai Bà Trưng",
        "Bà Triệu",
        "Đinh Bộ Lĩnh",
        "Lê Thánh Tông",
        "Phan Bội Châu",
        "Phan Châu Trinh",
        "Nguyễn Thị Minh Khai",
        "Tôn Đức Thắng",
        "Phạm Ngọc Thạch",
        "Nguyễn Văn Trỗi",
    ],

    # ============ ĐỊA DANH LỊCH SỬ ============
    "Địa danh lịch sử": [
        "Hoàng thành Thăng Long",
        "Cố đô Huế",
        "Địa đạo Củ Chi",
        "Nhà tù Côn Đảo",
        "Nhà tù Hỏa Lò",
        "Thành nhà Hồ",
        "Thánh địa Mỹ Sơn",
        "Khu di tích Pác Bó",
        "Chiến khu Việt Bắc",
        "Dinh Độc Lập",
    ],
}


def crawl_all_topics():
    """Crawl toàn bộ chủ đề."""
    total_docs = 0
    total_added = 0
    failed_topics = []

    # Đếm tổng số topic
    all_topics = []
    for category, topics in TOPICS.items():
        for topic in topics:
            all_topics.append((category, topic))

    print(f"{'='*60}")
    print(f"🚀 BẮT ĐẦU CRAWL {len(all_topics)} CHỦ ĐỀ LỊCH SỬ VIỆT NAM")
    print(f"{'='*60}\n")

    batch_docs = []
    batch_size = 10  # Index mỗi 10 docs

    for idx, (category, topic) in enumerate(all_topics):
        progress = f"[{idx+1}/{len(all_topics)}]"
        print(f"\n{progress} 📚 {category} → {topic}")

        try:
            wiki_results = search_wikipedia(topic, max_results=1)

            for doc in wiki_results:
                if is_already_crawled(doc["url"]):
                    print(f"  ⏭️ Đã crawl: {doc['title']}")
                    continue

                batch_docs.append(doc)
                mark_as_crawled(doc["url"], doc["title"], doc.get("source", "wikipedia"))
                total_docs += 1
                print(f"  ✅ {doc['title']} ({len(doc.get('content', ''))} chars)")

            # Index theo batch
            if len(batch_docs) >= batch_size:
                try:
                    added = add_new_documents(batch_docs)
                    total_added += added
                    print(f"\n  📦 Đã index batch: +{added} chunks (tổng: {total_added})")
                    batch_docs = []
                except Exception as e:
                    print(f"  ❌ Lỗi index batch: {e}")
                    batch_docs = []

        except Exception as e:
            print(f"  ❌ Lỗi: {e}")
            failed_topics.append(topic)

        # Delay để tránh bị Wikipedia block
        time.sleep(1)

    # Index batch cuối
    if batch_docs:
        try:
            added = add_new_documents(batch_docs)
            total_added += added
            print(f"\n📦 Index batch cuối: +{added} chunks")
        except Exception as e:
            print(f"❌ Lỗi index batch cuối: {e}")

    # Báo cáo
    print(f"\n{'='*60}")
    print(f"✅ HOÀN TẤT CRAWL")
    print(f"  📄 Tổng tài liệu: {total_docs}")
    print(f"  📦 Tổng chunks đã thêm: {total_added}")
    if failed_topics:
        print(f"  ❌ Thất bại ({len(failed_topics)}): {', '.join(failed_topics)}")
    print(f"{'='*60}")

    # Kiểm tra ChromaDB
    import chromadb
    from config import CHROMA_DB_PATH, COLLECTION_NAME
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    print(f"\n📊 ChromaDB hiện có: {collection.count()} chunks")


if __name__ == "__main__":
    crawl_all_topics()