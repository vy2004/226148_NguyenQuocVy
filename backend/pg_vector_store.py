"""
PostgreSQL Vector Store (không cần pgvector extension)
Dùng FLOAT[] + tính cosine similarity bằng SQL
"""
import psycopg2
import psycopg2.extras
import numpy as np
from sentence_transformers import SentenceTransformer
from db_config import DB_CONFIG, EMBEDDING_MODEL, EMBEDDING_DIM


class PgVectorStore:
    def __init__(self):
        self.conn = None
        self.model = None
        self._connect()
        self._create_tables()
        self._load_model()

    def _connect(self):
        """Kết nối PostgreSQL."""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.autocommit = True
            print(f"✅ Đã kết nối PostgreSQL: {DB_CONFIG['database']}")
        except Exception as e:
            print(f"❌ Lỗi kết nối PostgreSQL: {e}")
            raise e

    def _create_tables(self):
        """Tạo các bảng cần thiết."""
        cur = self.conn.cursor()

        # Bảng tai_lieu_lich_su - lưu tài liệu + embedding dạng FLOAT[]
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tai_lieu_lich_su (
                id SERIAL PRIMARY KEY,
                title TEXT,
                content TEXT NOT NULL,
                source TEXT,
                url TEXT,
                chunk_index INTEGER DEFAULT 0,
                embedding FLOAT[] DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Index cho tìm kiếm nhanh theo source
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_source
            ON tai_lieu_lich_su (source);
        """)

        # Index cho content (tránh trùng lặp)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_content_hash
            ON tai_lieu_lich_su (md5(content));
        """)

        # Bảng lich_su_nhan_tin hay chat_history
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lich_su_nhan_tin (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Index cho session_id
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_session
            ON lich_su_nhan_tin (session_id, created_at DESC);
        """)

        # Bảng nguon_tai_lieu hay crawled_sources
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nguon_tai_lieu (
                id SERIAL PRIMARY KEY,
                duong_dan_url TEXT UNIQUE NOT NULL,
                ten_nguon TEXT,
                loai_nguon TEXT,
                ngay_cap_nhat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Tạo function tính cosine similarity trong PostgreSQL
        cur.execute("""
            CREATE OR REPLACE FUNCTION cosine_similarity(a FLOAT[], b FLOAT[])
            RETURNS FLOAT AS $$
            DECLARE
                dot_product FLOAT := 0;
                norm_a FLOAT := 0;
                norm_b FLOAT := 0;
                i INTEGER;
            BEGIN
                IF array_length(a, 1) IS NULL OR array_length(b, 1) IS NULL THEN
                    RETURN 0;
                END IF;
                IF array_length(a, 1) != array_length(b, 1) THEN
                    RETURN 0;
                END IF;
                FOR i IN 1..array_length(a, 1) LOOP
                    dot_product := dot_product + (a[i] * b[i]);
                    norm_a := norm_a + (a[i] * a[i]);
                    norm_b := norm_b + (b[i] * b[i]);
                END LOOP;
                IF norm_a = 0 OR norm_b = 0 THEN
                    RETURN 0;
                END IF;
                RETURN dot_product / (sqrt(norm_a) * sqrt(norm_b));
            END;
            $$ LANGUAGE plpgsql IMMUTABLE;
        """)


        # Thêm cột tsvector cho Full-Text Search (Hybrid Search)
        cur.execute("""
            ALTER TABLE tai_lieu_lich_su
            ADD COLUMN IF NOT EXISTS tsv_content tsvector;
        """)

        # Cập nhật tsvector cho dữ liệu cũ (nếu chưa có)
        cur.execute("""
            UPDATE tai_lieu_lich_su
            SET tsv_content = to_tsvector('simple', content)
            WHERE tsv_content IS NULL;
        """)

        # Index GIN cho tìm kiếm Full-Text nhanh
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_tsvector
            ON tai_lieu_lich_su USING GIN(tsv_content);
        """)

        # Trigger tự động cập nhật tsvector khi thêm/sửa document
        cur.execute("""
            CREATE OR REPLACE FUNCTION update_tsv_content()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.tsv_content := to_tsvector('simple', NEW.content);
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)

        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_update_tsv'
                ) THEN
                    CREATE TRIGGER trg_update_tsv
                    BEFORE INSERT OR UPDATE ON tai_lieu_lich_su
                    FOR EACH ROW
                    EXECUTE FUNCTION update_tsv_content();
                END IF;
            END $$;
        """)
        cur.close()
        print("✅ Đã tạo tables + cosine_similarity function")

    def _load_model(self):
        """Load embedding model."""
        print(f"⏳ Đang load embedding model...")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"✅ Đã load embedding model (dim={EMBEDDING_DIM})")

    def _embed(self, texts):
        """Chuyển text thành vector."""
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings

    # =====================================================
    # QUẢN LÝ TÀI LIỆU
    # =====================================================

    def add_documents(self, docs):
        """Thêm tài liệu vào database."""
        if not docs:
            return 0

        cur = self.conn.cursor()
        added = 0

        for doc in docs:
            content = doc.get("content", "")
            title = doc.get("title", "Unknown")
            source = doc.get("source", "unknown")
            url = doc.get("url", "")

            chunks = self._split_text(content, chunk_size=500, overlap=50)

            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:
                    continue

                # Kiểm tra trùng lặp
                cur.execute("""
                    SELECT id FROM tai_lieu_lich_su
                    WHERE md5(content) = md5(%s)
                    LIMIT 1
                """, (chunk,))

                if cur.fetchone():
                    continue

                # Tạo embedding
                embedding = self._embed(chunk)[0]

                # Insert
                cur.execute("""
                    INSERT INTO tai_lieu_lich_su (title, content, source, url, chunk_index, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (title, chunk, source, url, i, embedding.tolist()))

                added += 1

        cur.close()
        print(f"📦 Đã thêm {added} chunks vào PostgreSQL")
        return added

    def _split_text(self, text, chunk_size=100, overlap=20):
        """Chia text thành chunks."""
        if not text:
            return []
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            if len(chunk.strip()) > 20:
                chunks.append(chunk)
            start = end - overlap
        return chunks

    def _rrf_fusion(self, vector_results, text_results, k=60):
        """Kết hợp kết quả bằng thuật toán Reciprocal Rank Fusion."""
        scores = {}

        # Tính điểm từ kết quả Vector
        for rank, res in enumerate(vector_results):
            doc_id = res['id']
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)

        # Tính điểm từ kết quả Text Search
        for rank, res in enumerate(text_results):
            doc_id = res['id']
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)

        # Sắp xếp lại theo điểm RRF
        sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Lấy thông tin chi tiết của các document đã được sắp xếp
        final_results = []
        all_docs = {d['id']: d for d in (vector_results + text_results)}

        for doc_id, score in sorted_ids:
            doc = all_docs[doc_id]
            doc['rrf_score'] = score
            final_results.append(doc)

        return final_results

    def search(self, query, n_results=10, min_similarity=0.3):
        """Tìm kiếm kết hợp Hybrid (Vector + Full-Text Search)."""
        # 1. Lấy kết quả từ Vector Search
        query_embedding = self._embed(query)[0]
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT id, title, content, source, url,
                   cosine_similarity(embedding, %s::FLOAT[]) AS similarity
            FROM tai_lieu_lich_su
            WHERE array_length(embedding, 1) > 0
            ORDER BY similarity DESC
            LIMIT %s
        """, (query_embedding.tolist(), n_results * 2))
        vector_results = cur.fetchall()

        # 2. Lấy kết quả từ Full-Text Search
        # Chuyển query thành định dạng tsquery (ví dụ: 'ngô & quyền')
        keywords = " & ".join(query.split())
        cur.execute("""
            SELECT id, title, content, source, url,
                   ts_rank(tsv_content, to_tsquery('simple', %s)) AS rank
            FROM tai_lieu_lich_su
            WHERE tsv_content @@ to_tsquery('simple', %s)
            ORDER BY rank DESC
            LIMIT %s
        """, (keywords, keywords, n_results * 2))
        text_results = cur.fetchall()
        cur.close()

        # 3. Kết hợp bằng RRF
        hybrid_results = self._rrf_fusion(vector_results, text_results)

        return hybrid_results[:n_results]

    def get_context(self, question, n_results=10):
        """Query và trả về context + sources."""
        results = self.search(question, n_results=n_results)

        if not results:
            return "", [], []

        context_parts = []
        sources = []

        for i, r in enumerate(results):
            source = r["source"]
            sim = r.get("rrf_score") or r.get("similarity") or 0
            if source not in sources:
                sources.append(source)
            context_parts.append(
                f"[Tài liệu {i+1} - {source}]:\n{r['content']}\n"
            )
            print(f"  📄 {i+1}. {source} (score={sim:.3f}) - {r['content'][:80]}...")

        context = "\n".join(context_parts)
        print(f"  📊 Tổng: {len(context)} ký tự từ {len(results)} chunks")
        return context, sources, results

    def count_documents(self):
        """Đếm tổng số chunks."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tai_lieu_lich_su")
        count = cur.fetchone()[0]
        cur.close()
        return count

    # =====================================================
    # LỊCH SỬ CHAT
    # =====================================================

    def save_chat(self, session_id, user_message, bot_response, sources=None):
        """Lưu lịch sử chat vào PostgreSQL."""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO lich_su_nhan_tin (session_id, user_message, bot_response, sources)
            VALUES (%s, %s, %s, %s)
        """, (session_id, user_message, bot_response, str(sources or [])))
        cur.close()

    def get_chat_history(self, session_id, max_turns=5):
        """Lấy lịch sử chat từ PostgreSQL."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT user_message, bot_response
            FROM lich_su_nhan_tin
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (session_id, max_turns))
        results = cur.fetchall()
        cur.close()
        return list(reversed(results))

    def clear_chat_history(self, session_id):
        """Xóa lịch sử chat."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM lich_su_nhan_tin WHERE session_id = %s", (session_id,))
        cur.close()

    # =====================================================
    # QUẢN LÝ NGUỒN ĐÃ CRAWL
    # =====================================================

    def is_crawled(self, url):
        """Kiểm tra URL đã crawl chưa."""
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM nguon_tai_lieu WHERE duong_dan_url = %s", (url,))
        result = cur.fetchone()
        cur.close()
        return result is not None

    def mark_crawled(self, url, title="", source_type=""):
        """Đánh dấu URL đã crawl."""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO nguon_tai_lieu (duong_dan_url, ten_nguon, loai_nguon)
            VALUES (%s, %s, %s)
            ON CONFLICT (duong_dan_url) DO NOTHING
        """, (url, title, source_type))
        cur.close()

    # =====================================================
    # THỐNG KÊ
    # =====================================================

    def get_stats(self):
        """Thống kê database."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT COUNT(*) as total FROM tai_lieu_lich_su")
        total_chunks = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(DISTINCT source) as total FROM tai_lieu_lich_su")
        total_sources = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as total FROM nguon_tai_lieu")
        total_crawled = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as total FROM lich_su_nhan_tin")
        total_chats = cur.fetchone()["total"]

        cur.execute("""
            SELECT source, COUNT(*) as chunks
            FROM tai_lieu_lich_su
            GROUP BY source
            ORDER BY chunks DESC
            LIMIT 10
        """)
        top_sources = cur.fetchall()

        cur.close()
        return {
            "total_chunks": total_chunks,
            "total_sources": total_sources,
            "total_crawled": total_crawled,
            "total_chats": total_chats,
            "top_sources": top_sources,
        }

    def close(self):
        """Đóng kết nối."""
        if self.conn:
            self.conn.close()
            print("🔌 Đã đóng kết nối PostgreSQL")