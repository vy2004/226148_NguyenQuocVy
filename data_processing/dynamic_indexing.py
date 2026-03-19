"""
Module dynamic indexing: Thêm tài liệu PDF mới vào ChromaDB mà không cần rebuild toàn bộ.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loader import load_pdf_file
from chunking import chunk_documents
from indexing import get_collection, is_document_indexed, _make_chunk_id


def add_new_documents(documents: list) -> int:
    """
    Thêm tài liệu mới vào ChromaDB.

    Args:
        documents: danh sách dict {"content": "...", "source": "..."}

    Returns:
        Số chunks đã thêm
    """
    if not documents:
        print("❌ Không có tài liệu mới để thêm!")
        return 0

    chunks = chunk_documents(documents)
    if not chunks:
        print("❌ Không tạo được chunks từ tài liệu!")
        return 0

    collection = get_collection()

    from indexing import get_embedding_function
    embedding_fn = get_embedding_function()
    embedding_fn.set_mode("passage")

    documents_list = []
    metadatas_list = []
    ids_list = []

    per_source_counter: dict[str, int] = {}

    for chunk in chunks:
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

        source = clean_metadata.get("source", "unknown")
        idx = per_source_counter.get(source, 0)
        per_source_counter[source] = idx + 1

        documents_list.append(content)
        metadatas_list.append(clean_metadata)
        ids_list.append(_make_chunk_id(source, idx))

    if not documents_list:
        print("❌ Không có nội dung hợp lệ để thêm!")
        return 0

    batch_size = 500
    total = len(documents_list)
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        collection.upsert(
            documents=documents_list[start:end],
            metadatas=metadatas_list[start:end],
            ids=ids_list[start:end],
        )

    embedding_fn.set_mode("query")

    print(f"✅ Đã thêm {total} chunks mới vào ChromaDB")
    print(f"📊 Tổng chunks hiện tại: {collection.count()}")
    return total


def add_pdf_file(filepath: str) -> int:
    """
    Thêm một file PDF mới vào ChromaDB.
    Nếu file đã được index trước đó thì bỏ qua.

    Args:
        filepath: đường dẫn đến file PDF

    Returns:
        Số chunks đã thêm (0 nếu đã index hoặc lỗi)
    """
    if not os.path.exists(filepath):
        print(f"❌ File không tồn tại: {filepath}")
        return 0

    filename = os.path.basename(filepath)

    if is_document_indexed(filename):
        print(f"⏭️ Bỏ qua '{filename}' -- đã được index trước đó")
        return 0

    try:
        content = load_pdf_file(filepath)
    except Exception as e:
        print(f"❌ Lỗi đọc PDF: {e}")
        return 0

    if not content or not content.strip():
        print(f"⚠️ File PDF rỗng hoặc không trích xuất được text: {filepath}")
        return 0

    documents = [{"content": content.strip(), "source": filename}]
    return add_new_documents(documents)