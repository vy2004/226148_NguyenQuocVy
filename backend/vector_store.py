import chromadb
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CHROMA_DB_PATH, COLLECTION_NAME, NUM_RESULTS

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        try:
            self.collection = self.client.get_collection(name=COLLECTION_NAME)
            print(f"✅ Đã kết nối ChromaDB: {self.collection.count()} chunks")
        except Exception as e:
            print(f"❌ Lỗi kết nối ChromaDB: {e}")
            self.collection = None
    
    def get_formatted_context(self, query, n_results=NUM_RESULTS, min_similarity=0.35):
        """
        Tìm kiếm tài liệu liên quan và lọc theo độ tương đồng.
        """
        if not self.collection:
            return "Không có dữ liệu.", []
        
        results = self.collection.query(query_texts=[query], n_results=n_results)
        
        if not results['documents'][0]:
            return "Không tìm thấy tài liệu liên quan.", []
        
        context_parts = []
        sources = []
        
        # Lấy similarity cao nhất để so sánh
        best_similarity = max(1 - d for d in results['distances'][0])
        
        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            similarity = 1 - dist
            
            # Chỉ lấy tài liệu có similarity >= ngưỡng
            # VÀ không quá thấp so với kết quả tốt nhất
            if similarity < min_similarity:
                continue
            if similarity < best_similarity * 0.7:
                continue
            
            source = meta.get('source', 'Không rõ nguồn')
            context_parts.append(
                f"[Tài liệu {len(context_parts)+1} - Nguồn: {source} - Độ liên quan: {similarity:.2f}]\n{doc}"
            )
            if source not in sources:
                sources.append(source)
        
        if not context_parts:
            return "Không tìm thấy tài liệu đủ liên quan.", []
        
        context = "\n\n---\n\n".join(context_parts)
        return context, sources