import chromadb
import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_vector_database(chunks, db_path="chroma_db", collection_name="vietnam_history"):
    print("Đang khởi tạo ChromaDB...")
    
    client = chromadb.PersistentClient(path=db_path)
    
    try:
        client.delete_collection(name=collection_name)
        print(f"Đã xóa collection cũ: {collection_name}")
    except:
        pass
    
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    
    print(f"Đang thêm {len(chunks)} chunks vào vector database...")
    
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        ids = [f"chunk_{i + j}" for j in range(len(batch))]
        documents = [chunk['text'] for chunk in batch]
        metadatas = [chunk['metadata'] for chunk in batch]
        
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"  Đã thêm batch {i // batch_size + 1}: {len(batch)} chunks")
    
    total = collection.count()
    print(f"\nHoàn tất! Tổng số chunks trong database: {total}")
    return collection

def test_search(db_path="chroma_db", collection_name="vietnam_history"):
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection(name=collection_name)
    
    test_queries = [
        "Trận Bạch Đằng năm 938 diễn ra như thế nào?",
        "Ai là người sáng lập nhà Lý?",
        "Chiến dịch Điện Biên Phủ có ý nghĩa gì?",
    ]
    
    print("\nTEST TÌM KIẾM:")
    for query in test_queries:
        print(f"\n📝 Câu hỏi: {query}")
        results = collection.query(query_texts=[query], n_results=2)
        
        for j, (doc, meta, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            print(f"  Kết quả {j+1} (similarity: {1-distance:.4f}):")
            print(f"  Nguồn: {meta['source']}")
            print(f"  Nội dung: {doc[:150]}...")

if __name__ == "__main__":
    chunks_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'chunks.json')
    
    if not os.path.exists(chunks_path):
        print("Chưa có file chunks.json! Chạy chunking.py trước")
        exit(1)
    
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    db_path = os.path.join(os.path.dirname(__file__), '..', 'chroma_db')
    create_vector_database(chunks, db_path=db_path)
    test_search(db_path=db_path)