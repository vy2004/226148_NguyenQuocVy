import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loader import load_all_documents
from chunking import chunk_documents, save_chunks
from indexing import create_vector_database, test_search

def main():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_dir, 'data', 'raw')
    processed_dir = os.path.join(project_dir, 'data', 'processed')
    db_path = os.path.join(project_dir, 'chroma_db')
    
    print("=" * 60)
    print("  PIPELINE XỬ LÝ DỮ LIỆU LỊCH SỬ VIỆT NAM")
    print("=" * 60)
    
    # BƯỚC 1
    print("\n📖 BƯỚC 1: Đọc tài liệu")
    documents = load_all_documents(data_dir)
    
    if not documents:
        print("\n❌ Không tìm thấy tài liệu nào!")
        print("Hãy thêm file .txt vào thư mục data/raw/")
        return
    
    # BƯỚC 2
    print("\n✂️ BƯỚC 2: Chia nhỏ tài liệu")
    chunks = chunk_documents(documents)
    chunks_path = os.path.join(processed_dir, 'chunks.json')
    save_chunks(chunks, chunks_path)
    
    # BƯỚC 3
    print("\n🗄️ BƯỚC 3: Tạo Vector Database")
    create_vector_database(chunks, db_path=db_path)
    
    # BƯỚC 4
    print("\n🔍 BƯỚC 4: Test tìm kiếm")
    test_search(db_path=db_path)
    
    print("\n" + "=" * 60)
    print(f"✅ HOÀN TẤT! Tài liệu: {len(documents)} | Chunks: {len(chunks)}")
    print("=" * 60)

if __name__ == "__main__":
    main()