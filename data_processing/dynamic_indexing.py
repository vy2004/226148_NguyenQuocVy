"""
Chunk và index dữ liệu mới crawl được vào PostgreSQL realtime.
"""
import sys
import os
import hashlib

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from backend.pg_vector_store import PgVectorStore


def add_new_documents(documents: list[dict], chunk_size: int = 800, overlap: int = 200) -> int:
    """
    Index dữ liệu mới vào PostgreSQL.
    documents: [{"title": ..., "content": ..., "url": ..., "source": ...}]
    Trả về số chunk đã thêm.
    """
    pg_store = PgVectorStore()
    added = pg_store.add_documents(documents)
    print(f"Đã thêm {added} chunk mới vào PostgreSQL")
    pg_store.close()
    return added