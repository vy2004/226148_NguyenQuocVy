"""
Chunk và index dữ liệu mới crawl được vào ChromaDB realtime.
"""
import sys
import os
import hashlib

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION_NAME = "vietnam_history"


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


def split_text(text: str, chunk_size: int = 800, overlap: int = 200) -> list[str]:
    """Chia text thành các chunk nhỏ."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
        length_function=len
    )
    chunks = splitter.split_text(text)
    # Lọc chunk quá ngắn
    return [c for c in chunks if len(c.strip()) >= 50]


def generate_chunk_id(text: str) -> str:
    """Tạo ID duy nhất cho chunk."""
    return hashlib.md5(text.encode()).hexdigest()


def is_duplicate(collection, chunk_text: str) -> bool:
    """Kiểm tra chunk đã tồn tại chưa."""
    chunk_id = generate_chunk_id(chunk_text)
    try:
        existing = collection.get(ids=[chunk_id])
        return len(existing["ids"]) > 0
    except:
        return False


def add_new_documents(documents: list[dict], chunk_size: int = 800, overlap: int = 200) -> int:
    """
    Chunk + index dữ liệu mới vào ChromaDB.
    documents: [{"title": ..., "content": ..., "url": ..., "source": ...}]
    Trả về số chunk đã thêm.
    """
    collection = get_collection()
    added = 0

    for doc in documents:
        content = doc.get("content", "")
        if not content or len(content.strip()) < 100:
            continue

        chunks = split_text(content, chunk_size=chunk_size, overlap=overlap)

        for i, chunk_text in enumerate(chunks):
            if is_duplicate(collection, chunk_text):
                continue

            chunk_id = generate_chunk_id(chunk_text)
            metadata = {
                "source": doc.get("title", "Unknown"),
                "url": doc.get("url", ""),
                "origin": doc.get("source", "web"),
                "chunk_index": i,
            }

            collection.add(
                ids=[chunk_id],
                documents=[chunk_text],
                metadatas=[metadata]
            )
            added += 1

    print(f"Đã thêm {added} chunk mới vào ChromaDB")
    return added