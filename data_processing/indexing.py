"""
Module indexing: Tạo vector database bằng ChromaDB
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict

# Cấu hình ChromaDB
CHROMA_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "chromadb"
)
COLLECTION_NAME = "vietnam_history"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def get_chroma_client():
    """Tạo ChromaDB client với persistent storage."""
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client


def get_embedding_function():
    """Tạo embedding function sử dụng sentence-transformers."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )


def get_collection():
    """Lấy hoặc tạo collection trong ChromaDB."""
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def create_vector_database(chunks: List[Dict]):
    """
    Tạo vector database từ danh sách chunks.
    Mỗi chunk có dạng: {"content": "...", "metadata": {...}}
    """
    if not chunks:
        print("❌ Không có chunks để index!")
        return

    collection = get_collection()

    documents = []
    metadatas = []
    ids = []

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

        documents.append(content)
        metadatas.append(clean_metadata)
        ids.append(f"chunk_{i}")

    batch_size = 500
    total = len(documents)

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        collection.upsert(
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end]
        )
        print(f"  ✅ Đã index {end}/{total} chunks")

    print(f"\n✅ Tổng cộng {total} chunks đã được index vào ChromaDB")
    print(f"📁 Dữ liệu lưu tại: {CHROMA_PERSIST_DIR}")


def search(query: str, top_k: int = 5) -> List[Dict]:
    """
    Tìm kiếm tài liệu liên quan đến câu hỏi.
    """
    collection = get_collection()

    if collection.count() == 0:
        print("⚠️ Database trống! Hãy chạy pipeline trước.")
        return []

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    search_results = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            result = {
                "content": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "score": 1 - results["distances"][0][i] if results["distances"] else 0
            }
            search_results.append(result)

    return search_results


def test_search():
    """Test tìm kiếm với một số câu hỏi mẫu."""
    test_queries = [
        "Trận Bạch Đằng năm 938",
        "Triều đại nhà Lý",
        "Chiến thắng Điện Biên Phủ",
        "Vua Quang Trung đại phá quân Thanh",
        "Cách mạng tháng Tám 1945"
    ]

    collection = get_collection()
    total_chunks = collection.count()
    print(f"\n📊 Tổng số chunks trong database: {total_chunks}")

    if total_chunks == 0:
        print("⚠️ Database trống!")
        return

    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        results = search(query, top_k=3)
        for j, r in enumerate(results):
            score = r["score"]
            content_preview = r["content"][:100] + "..."
            print(f"  [{j+1}] (score: {score:.4f}) {content_preview}")


def delete_collection():
    """Xóa toàn bộ collection trong ChromaDB."""
    client = get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"✅ Đã xóa collection '{COLLECTION_NAME}'")
    except Exception as e:
        print(f"⚠️ Lỗi khi xóa collection: {e}")


def get_stats() -> Dict:
    """Lấy thống kê về database."""
    collection = get_collection()
    return {
        "collection_name": COLLECTION_NAME,
        "total_chunks": collection.count(),
        "persist_dir": CHROMA_PERSIST_DIR,
        "embedding_model": EMBEDDING_MODEL
    }