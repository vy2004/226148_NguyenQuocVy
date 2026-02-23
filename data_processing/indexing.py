"""
Tạo index trong PostgreSQL từ danh sách chunks.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from pg_vector_store import PgVectorStore


def create_vector_database(chunks):
    """Index chunks vào PostgreSQL."""
    print("Đang kết nối PostgreSQL...")
    pg_store = PgVectorStore()

    print(f"Đang thêm {len(chunks)} chunks vào PostgreSQL...")

    # Chuyển chunks thành format phù hợp với PgVectorStore
    docs = []
    for chunk in chunks:
        docs.append({
            "title": chunk["metadata"].get("source", "Unknown"),
            "content": chunk["text"],
            "source": chunk["metadata"].get("source", "unknown"),
            "url": "",
        })

    # Thêm theo batch
    batch_size = 50
    total_added = 0
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        added = pg_store.add_documents(batch)
        total_added += added
        print(f"  Đã xử lý batch {i // batch_size + 1}: +{added} chunks")

    total = pg_store.count_documents()
    print(f"\nHoàn tất! Tổng số chunks trong PostgreSQL: {total}")

    pg_store.close()
    return total_added


def test_search():
    """Test tìm kiếm trong PostgreSQL."""
    pg_store = PgVectorStore()

    test_queries = [
        "Trận Bạch Đằng năm 938 diễn ra như thế nào?",
        "Ai là người sáng lập nhà Lý?",
        "Chiến dịch Điện Biên Phủ có ý nghĩa gì?",
    ]

    print("\nTEST TÌM KIẾM:")
    for query in test_queries:
        print(f"\n📝 Câu hỏi: {query}")
        results = pg_store.search(query, n_results=2)

        for j, r in enumerate(results):
            score = r.get("rrf_score") or r.get("similarity") or 0
            print(f"  Kết quả {j+1} (score: {score:.4f}):")
            print(f"  Nguồn: {r['source']}")
            print(f"  Nội dung: {r['content'][:150]}...")

    pg_store.close()


if __name__ == "__main__":
    import json

    chunks_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'chunks.json')

    if not os.path.exists(chunks_path):
        print("Chưa có file chunks.json! Chạy chunking.py trước")
        exit(1)

    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    create_vector_database(chunks)
    test_search()