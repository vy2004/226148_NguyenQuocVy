"""
Pipeline xử lý dữ liệu: Đọc PDF → Chia chunks → Index vào ChromaDB
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from loader import load_all_documents
from chunking import chunk_documents, save_chunks
from indexing import create_vector_database, test_search, get_indexed_sources
from backend.runtime_paths import PDF_DIR, PROCESSED_DIR


def main():
    print("=" * 60)
    print("  PIPELINE XỬ LÝ DỮ LIỆU LỊCH SỬ VIỆT NAM")
    print("  (PDF → ChromaDB Vector Store)")
    print("=" * 60)

    # BƯỚC 1: Đọc tất cả PDF
    print("\n📖 BƯỚC 1: Đọc tài liệu PDF")
    all_documents = load_all_documents(PDF_DIR)

    if not all_documents:
        print("\n❌ Không tìm thấy tài liệu nào!")
        print(f"Hãy thêm file .pdf vào thư mục {PDF_DIR}")
        return

    # BƯỚC 2: Lọc bỏ tài liệu đã index
    print("\n🔎 BƯỚC 2: Kiểm tra tài liệu đã index")
    indexed_sources = get_indexed_sources()
    new_documents = [
        doc for doc in all_documents
        if doc["source"] not in indexed_sources
    ]
    skipped = len(all_documents) - len(new_documents)

    if skipped:
        print(f"  ⏭️ Bỏ qua {skipped} tài liệu đã index trước đó")
    if not new_documents:
        print("  ✅ Tất cả tài liệu đã được index, không cần xử lý thêm.")
        test_search()
        return

    print(f"  📄 Sẽ index {len(new_documents)} tài liệu mới")

    # BƯỚC 3: Chia nhỏ tài liệu mới
    print("\n✂️ BƯỚC 3: Chia nhỏ tài liệu")
    chunks = chunk_documents(new_documents)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    chunks_path = os.path.join(PROCESSED_DIR, "chunks.json")
    save_chunks(chunks, chunks_path)

    # BƯỚC 4: Index vào ChromaDB
    print("\n🗄️ BƯỚC 4: Index vào ChromaDB")
    create_vector_database(chunks)

    # BƯỚC 5: Test tìm kiếm
    print("\n🔍 BƯỚC 5: Test tìm kiếm")
    test_search()

    print("\n" + "=" * 60)
    print(f"✅ HOÀN TẤT! Tổng PDF: {len(all_documents)} | Mới: {len(new_documents)} | Bỏ qua: {skipped} | Chunks mới: {len(chunks)}")
    print("=" * 60)


if __name__ == "__main__":
    main()