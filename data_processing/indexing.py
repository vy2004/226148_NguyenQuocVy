"""
Module indexing: Tạo vector database bằng ChromaDB
Sử dụng multilingual-e5-base cho embedding tiếng Việt chất lượng cao.
"""

import os
import chromadb
from typing import List, Dict
from sentence_transformers import SentenceTransformer

# Cấu hình ChromaDB
CHROMA_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "csdl_vector"
)
COLLECTION_NAME = "lich_su_viet_nam"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"


# ======================== CUSTOM EMBEDDING ========================

class E5EmbeddingFunction:
    """
    Embedding function cho model intfloat/multilingual-e5-base.
    Model E5 yêu cầu prefix "query: " hoặc "passage: " trước mỗi text.
    - Khi index tài liệu: dùng "passage: "
    - Khi tìm kiếm: dùng "query: "
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        print(f"[Embedding] Loading model: {model_name} ...")
        self._model = SentenceTransformer(model_name)
        self._mode = "query"  # Mặc định là query (search)
        print(f"[Embedding] ✅ Model loaded ({self._model.get_sentence_embedding_dimension()} dims)")

    def set_mode(self, mode: str):
        """Chuyển mode: 'query' cho tìm kiếm, 'passage' cho index tài liệu."""
        assert mode in ("query", "passage"), f"Mode phải là 'query' hoặc 'passage', nhận: {mode}"
        self._mode = mode

    def __call__(self, input: List[str]) -> List[List[float]]:
        prefix = "query: " if self._mode == "query" else "passage: "
        prefixed = [prefix + text for text in input]
        embeddings = self._model.encode(prefixed, normalize_embeddings=True)
        return embeddings.tolist()


# Singleton embedding function (tránh load model nhiều lần)
_embedding_fn_instance = None


def get_embedding_function() -> E5EmbeddingFunction:
    """Lấy embedding function (singleton, chỉ load model 1 lần)."""
    global _embedding_fn_instance
    if _embedding_fn_instance is None:
        _embedding_fn_instance = E5EmbeddingFunction(EMBEDDING_MODEL)
    return _embedding_fn_instance


def get_chroma_client():
    """Tạo ChromaDB client với persistent storage."""
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client


def get_collection():
    """Lấy hoặc tạo collection trong ChromaDB."""
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    # Đảm bảo mode query khi sử dụng collection bình thường
    embedding_fn.set_mode("query")
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

    # Chuyển sang mode "passage" khi index tài liệu
    embedding_fn = get_embedding_function()
    embedding_fn.set_mode("passage")

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

    # Chuyển lại mode "query" sau khi index xong
    embedding_fn.set_mode("query")

    print(f"\n✅ Tổng cộng {total} chunks đã được index vào ChromaDB")
    print(f"📁 Dữ liệu lưu tại: {CHROMA_PERSIST_DIR}")
    print(f"🧠 Embedding model: {EMBEDDING_MODEL}")


def search(query: str, top_k: int = 5, max_distance: float = 0.8) -> List[Dict]:
    """
    Tìm kiếm tài liệu liên quan đến câu hỏi.
    ChromaDB cosine distance: 0 = giống nhất, 2 = khác nhất.
    max_distance: ngưỡng tối đa, chỉ trả về kết quả có distance < max_distance.
    """
    collection = get_collection()

    if collection.count() == 0:
        print("[Search] ⚠️ Database rỗng! Chạy run_pipeline.py trước.")
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k * 2, 20),  # Lấy nhiều hơn rồi lọc
        include=["documents", "metadatas", "distances"]
    )

    search_results = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            if dist < max_distance:  # Chỉ lấy kết quả đủ tốt
                search_results.append({
                    "content": doc,
                    "metadata": meta,
                    "score": dist
                })

    # Sắp xếp theo score (distance thấp = tốt hơn)
    search_results.sort(key=lambda x: x["score"])

    return search_results[:top_k]


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