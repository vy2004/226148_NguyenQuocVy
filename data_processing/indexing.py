"""
Module indexing: Tạo vector database bằng ChromaDB
Sử dụng multilingual-e5-base cho embedding tiếng Việt chất lượng cao.
"""

import os
import sys
import chromadb
from typing import List, Dict
from sentence_transformers import SentenceTransformer
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.runtime_paths import VECTOR_DIR

# Cấu hình ChromaDB
CHROMA_PERSIST_DIR = VECTOR_DIR
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

    def name(self) -> str:
        """Tên ổn định để ChromaDB có thể persist/check embedding config."""
        return f"e5_embedding_{EMBEDDING_MODEL}"

    def set_mode(self, mode: str):
        """Chuyển mode: 'query' cho tìm kiếm, 'passage' cho index tài liệu."""
        assert mode in ("query", "passage"), f"Mode phải là 'query' hoặc 'passage', nhận: {mode}"
        self._mode = mode

    def __call__(self, input: List[str]) -> List[List[float]]:
        prefix = "query: " if self._mode == "query" else "passage: "
        prefixed = [prefix + text for text in input]
        embeddings = self._model.encode(prefixed, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, input: List[str]) -> List[List[float]]:
        """Tương thích với interface embedding mới của ChromaDB khi query."""
        self.set_mode("query")
        return self.__call__(input)

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        """Tương thích với interface embedding mới của ChromaDB khi index."""
        self.set_mode("passage")
        return self.__call__(input)


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


def get_indexed_sources() -> set:
    """Trả về tập hợp tên file (source) đã được index trong ChromaDB."""
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return set()

    batch_size = 10000
    sources: set = set()
    for offset in range(0, total, batch_size):
        result = collection.get(
            limit=batch_size,
            offset=offset,
            include=["metadatas"],
        )
        for meta in result.get("metadatas", []):
            src = (meta or {}).get("source")
            if src:
                sources.add(src)
    return sources


def is_document_indexed(source_name: str) -> bool:
    """Kiểm tra xem tài liệu (theo tên file) đã được index chưa."""
    collection = get_collection()
    result = collection.get(
        where={"source": source_name},
        limit=1,
        include=[],
    )
    return len(result.get("ids", [])) > 0


def delete_chunks_by_source(source_name: str) -> int:
    """Xóa tất cả chunk thuộc một tài liệu. Trả về số chunk đã xóa."""
    collection = get_collection()
    result = collection.get(
        where={"source": source_name},
        include=[],
    )
    ids_to_delete = result.get("ids", [])
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
        print(f"[Index] 🗑️ Đã xóa {len(ids_to_delete)} chunks của '{source_name}'")
    return len(ids_to_delete)


def _make_chunk_id(source: str, chunk_index: int) -> str:
    """Tạo ID ổn định cho chunk dựa trên tên nguồn + thứ tự."""
    return f"{source}__chunk_{chunk_index}"


def create_vector_database(chunks: List[Dict]):
    """
    Tạo vector database từ danh sách chunks.
    Mỗi chunk có dạng: {"content": "...", "metadata": {...}}
    ID mỗi chunk = "{source}__chunk_{i}" để tránh ghi đè giữa các tài liệu.
    """
    if not chunks:
        print("❌ Không có chunks để index!")
        return

    collection = get_collection()
    embedding_fn = get_embedding_function()
    embedding_fn.set_mode("passage")

    documents = []
    metadatas = []
    ids = []

    per_source_counter: Dict[str, int] = {}

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

        documents.append(content)
        metadatas.append(clean_metadata)
        ids.append(_make_chunk_id(source, idx))

    batch_size = 500
    total = len(documents)
    skipped_existing = 0
    inserted_new = 0

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch_ids = ids[start:end]
        existing = collection.get(ids=batch_ids, include=[])
        existing_ids = set(existing.get("ids", []) if existing else [])

        filtered_docs = []
        filtered_metas = []
        filtered_ids = []
        for doc, meta, chunk_id in zip(
            documents[start:end],
            metadatas[start:end],
            batch_ids,
        ):
            if chunk_id in existing_ids:
                skipped_existing += 1
                continue
            filtered_docs.append(doc)
            filtered_metas.append(meta)
            filtered_ids.append(chunk_id)

        if not filtered_ids:
            continue

        collection.upsert(
            documents=filtered_docs,
            metadatas=filtered_metas,
            ids=filtered_ids
        )
        inserted_new += len(filtered_ids)
        print(f"  ✅ Đã index mới {inserted_new}/{total} chunks")

    embedding_fn.set_mode("query")

    print(f"\n✅ Tổng cộng {inserted_new} chunks mới đã được index vào ChromaDB")
    if skipped_existing:
        print(f"⏭️ Bỏ qua {skipped_existing} chunks đã tồn tại")
    print(f"📁 Dữ liệu lưu tại: {CHROMA_PERSIST_DIR}")
    print(f"🧠 Embedding model: {EMBEDDING_MODEL}")


def search(query: str, top_k: int = 5, max_distance: float = 0.8) -> List[Dict]:
    """
    Tìm kiếm tài liệu liên quan đến câu hỏi.
    ChromaDB cosine distance: 0 = giống nhất, 2 = khác nhất.
    max_distance: ngưỡng tối đa, chỉ trả về kết quả có distance < max_distance.
    """
    collection = get_collection()
    # Đảm bảo query luôn dùng đúng prefix "query: "
    get_embedding_function().set_mode("query")

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