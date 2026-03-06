"""
Module chunking: Chia văn bản thành các đoạn nhỏ (chunks) để index vào ChromaDB.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
import os


def chunk_documents(documents, chunk_size=800, chunk_overlap=200):
    """
    Chia danh sách tài liệu thành chunks nhỏ.
    
    Args:
        documents: list[dict] — mỗi dict có {"content": ..., "source": ...}
        chunk_size: kích thước mỗi chunk (ký tự)
        chunk_overlap: số ký tự chồng lấp giữa các chunk
    
    Returns:
        list[dict] — danh sách chunks {"content": ..., "metadata": {...}}
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
        length_function=len,
    )

    all_chunks = []

    for doc in documents:
        content = doc.get("content", "")
        source = doc.get("source", "unknown")

        splits = text_splitter.split_text(content)

        for i, split_text in enumerate(splits):
            chunk = {
                "content": split_text.strip(),
                "metadata": {
                    "source": source,
                    "chunk_index": i,
                    "total_chunks": len(splits),
                },
            }
            if len(chunk["content"]) > 50:
                all_chunks.append(chunk)

    print(f"  📦 Đã tạo {len(all_chunks)} chunks từ {len(documents)} tài liệu")
    return all_chunks


def save_chunks(chunks, output_path="data/processed/chunks.json"):
    """Lưu chunks ra file JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"  💾 Đã lưu {len(chunks)} chunks vào {output_path}")


if __name__ == "__main__":
    from loader import load_all_documents

    print("BƯỚC 1: Đọc tài liệu PDF")
    docs = load_all_documents()

    print("\nBƯỚC 2: Chia nhỏ tài liệu")
    chunks = chunk_documents(docs)

    print("\nBƯỚC 3: Lưu kết quả")
    save_chunks(chunks)

    print("\nMẪU 3 CHUNKS ĐẦU TIÊN:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Nguồn: {chunk['metadata']['source']}")
        print(f"Nội dung: {chunk['content'][:200]}...")