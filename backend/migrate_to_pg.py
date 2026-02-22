"""
Chuyển toàn bộ data từ ChromaDB sang PostgreSQL.
Chạy 1 lần sau khi cài PostgreSQL.
"""
import sys
import os
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))
sys.path.insert(0, os.path.join(ROOT_DIR, "data_collection"))
sys.path.insert(0, os.path.join(ROOT_DIR, "data_processing"))

import chromadb
from config import CHROMA_DB_PATH, COLLECTION_NAME
from pg_vector_store import PgVectorStore


def migrate():
    print(f"{'='*60}")
    print(f"🚀 CHUYỂN DATA TỪ ChromaDB → PostgreSQL")
    print(f"{'='*60}\n")

    # Kết nối ChromaDB
    print("[1/4] Kết nối ChromaDB...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
        total = collection.count()
        print(f"  ✅ ChromaDB có {total} chunks\n")
    except Exception as e:
        print(f"  ❌ Không tìm thấy collection: {e}")
        return

    # Kết nối PostgreSQL
    print("[2/4] Kết nối PostgreSQL...")
    pg_store = PgVectorStore()
    pg_before = pg_store.count_documents()
    print(f"  ✅ PostgreSQL hiện có {pg_before} chunks\n")

    # Lấy data từ ChromaDB và chuyển sang PostgreSQL
    print("[3/4] Đang chuyển data...")
    batch_size = 50
    offset = 0
    total_added = 0
    total_skipped = 0

    while offset < total:
        try:
            results = collection.get(
                limit=batch_size,
                offset=offset,
                include=["documents", "metadatas"]
            )

            if not results["documents"]:
                break

            docs = []
            for doc, meta in zip(results["documents"], results["metadatas"]):
                if not doc or len(doc.strip()) < 50:
                    total_skipped += 1
                    continue

                docs.append({
                    "title": meta.get("source", "Unknown"),
                    "content": doc,
                    "source": meta.get("source", "unknown"),
                    "url": meta.get("url", ""),
                })

            if docs:
                added = pg_store.add_documents(docs)
                total_added += added

            processed = min(offset + batch_size, total)
            print(f"  📦 Đã xử lý: {processed}/{total} (thêm: {total_added}, bỏ qua: {total_skipped})")

        except Exception as e:
            print(f"  ❌ Lỗi batch {offset}: {e}")

        offset += batch_size
        time.sleep(0.1)

    # Báo cáo
    pg_after = pg_store.count_documents()
    print(f"\n{'='*60}")
    print(f"[4/4] ✅ HOÀN TẤT CHUYỂN DATA")
    print(f"  📊 ChromaDB: {total} chunks")
    print(f"  📊 PostgreSQL trước: {pg_before} chunks")
    print(f"  📊 PostgreSQL sau: {pg_after} chunks")
    print(f"  ✅ Đã thêm: {total_added} chunks")
    print(f"  ⏭️ Bỏ qua: {total_skipped} chunks (trùng/quá ngắn)")
    print(f"{'='*60}")

    pg_store.close()


if __name__ == "__main__":
    migrate()