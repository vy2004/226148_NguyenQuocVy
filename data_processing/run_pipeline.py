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
from indexing import create_vector_database, test_search
from backend.runtime_paths import PDF_DIR, PROCESSED_DIR


def main():
    print("=" * 60)
    print("  PIPELINE XỬ LÝ DỮ LIỆU LỊCH SỬ VIỆT NAM")
    print("  (PDF → ChromaDB Vector Store)")
    print("=" * 60)

    # BƯỚC 1
    print("\n📖 BƯỚC 1: Đọc tài liệu PDF")
    documents = load_all_documents(PDF_DIR)

    if not documents:
        print("\n❌ Không tìm thấy tài liệu nào!")
        print(f"Hãy thêm file .pdf vào thư mục {PDF_DIR}")
        return

    # BƯỚC 2
    print("\n✂️ BƯỚC 2: Chia nhỏ tài liệu")
    chunks = chunk_documents(documents)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    chunks_path = os.path.join(PROCESSED_DIR, "chunks.json")
    save_chunks(chunks, chunks_path)

    # BƯỚC 3
    print("\n🗄️ BƯỚC 3: Index vào ChromaDB")
    create_vector_database(chunks)

    # BƯỚC 4
    print("\n🔍 BƯỚC 4: Test tìm kiếm")
    test_search()

    print("\n" + "=" * 60)
    print(f"✅ HOÀN TẤT! Tài liệu: {len(documents)} | Chunks: {len(chunks)}")
    print("=" * 60)


if __name__ == "__main__":
    main()