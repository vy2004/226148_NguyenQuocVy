"""
Module dynamic indexing: Thêm tài liệu mới vào ChromaDB mà không cần rebuild toàn bộ.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chunking import chunk_documents
from indexing import get_collection


def add_new_documents(documents: list) -> int:
    """
    Thêm tài liệu mới vào ChromaDB.
    
    Args:
        documents: danh sách dict {"content": "...", "metadata": {...}}
    
    Returns:
        Số chunks đã thêm
    """
    if not documents:
        print("❌ Không có tài liệu mới để thêm!")
        return 0

    # Chia nhỏ tài liệu thành chunks
    chunks = chunk_documents(documents)
    if not chunks:
        print("❌ Không tạo được chunks từ tài liệu!")
        return 0

    collection = get_collection()
    existing_count = collection.count()

    documents_list = []
    metadatas_list = []
    ids_list = []

    for i, chunk in enumerate(chunks):
        content = chunk.get("content", "").strip()
        if not content:
            continue

        metadata = chunk.get("metadata", {})
        clean_metadata = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                clean_metadata[k] = v
            else:
                clean_metadata[k] = str(v)

        documents_list.append(content)
        metadatas_list.append(clean_metadata)
        ids_list.append(f"chunk_{existing_count + i}")

    if not documents_list:
        print("❌ Không có nội dung hợp lệ để thêm!")
        return 0

    # Thêm vào ChromaDB theo batch
    batch_size = 500
    total = len(documents_list)
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        collection.upsert(
            documents=documents_list[start:end],
            metadatas=metadatas_list[start:end],
            ids=ids_list[start:end]
        )

    print(f"✅ Đã thêm {total} chunks mới vào ChromaDB")
    print(f"📊 Tổng chunks hiện tại: {collection.count()}")
    return total


def add_raw_text(text: str, source: str = "unknown") -> int:
    """
    Thêm một đoạn văn bản thô vào ChromaDB.
    
    Args:
        text: nội dung văn bản
        source: tên nguồn
    
    Returns:
        Số chunks đã thêm
    """
    if not text or not text.strip():
        return 0

    documents = [{
        "content": text.strip(),
        "metadata": {"source": source}
    }]
    return add_new_documents(documents)