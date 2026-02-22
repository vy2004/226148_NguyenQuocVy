"""
RAG Chain sử dụng PostgreSQL (không cần pgvector)
"""
import sys
import os
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_COLLECTION_DIR = os.path.join(ROOT_DIR, "data_collection")
DATA_PROCESSING_DIR = os.path.join(ROOT_DIR, "data_processing")

for p in [ROOT_DIR, BACKEND_DIR, DATA_COLLECTION_DIR, DATA_PROCESSING_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import USE_GROQ, GEMINI_API_KEY
from pg_vector_store import PgVectorStore

# ============ LLM Setup ============
if USE_GROQ:
    from groq import Groq
    groq_key = os.getenv("GROQ_API_KEY")
    groq_client = Groq(api_key=groq_key)
    print("✅ Đã kết nối Groq API")
else:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    print("✅ Đã kết nối Gemini API")

# ============ PostgreSQL Vector Store ============
pg_store = PgVectorStore()
print(f"📊 PostgreSQL có {pg_store.count_documents()} chunks")

NO_INFO_KEYWORDS = [
    "không có thông tin", "không tìm thấy", "không chứa",
    "không đề cập", "không đủ thông tin", "xin lỗi, nhưng",
    "không có thông tin cụ thể", "không có thông tin trực tiếp",
    "chưa có thông tin", "không được đề cập",
]


def _call_llm(prompt: str) -> str:
    """Gọi LLM với retry."""
    for attempt in range(3):
        try:
            if USE_GROQ:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Bạn là chuyên gia lịch sử Việt Nam uyên bác. Phân tích kỹ tài liệu và trả lời chi tiết, chính xác bằng tiếng Việt."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=3000
                )
                return response.choices[0].message.content
            else:
                response = gemini_model.generate_content(prompt)
                return response.text
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait_time = 20 * (attempt + 1)
                print(f"⏳ Rate limit! Đợi {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e


def _answer_lacks_info(answer: str) -> bool:
    """Kiểm tra LLM có thiếu thông tin không."""
    return any(kw in answer.lower() for kw in NO_INFO_KEYWORDS)


def _extract_keywords(question: str) -> str:
    """Trích xuất từ khóa từ câu hỏi."""
    remove = ["bạn", "có", "biết", "gì", "về", "không", "cho", "tôi",
              "hãy", "kể", "nói", "là", "như", "thế", "nào", "ra", "sao",
              "được", "của", "và", "hay", "với", "trong", "này", "đó",
              "ở", "từ", "đến", "ạ", "vậy", "thì", "ai", "người", "nào", "vào"]
    words = question.lower().replace("?", "").replace("!", "").split()
    keywords = [w for w in words if w not in remove and len(w) > 1]
    return " ".join(keywords) if keywords else question


def crawl_and_index(query: str) -> int:
    """Crawl Wikipedia + Google, index vào PostgreSQL."""
    from wiki_crawler import search_wikipedia
    try:
        from google_search import google_search as do_google_search, scrape_page
        has_google = True
    except ImportError:
        has_google = False

    search_query = _extract_keywords(query)
    new_docs = []

    # Wikipedia
    print(f"[Crawl] Wikipedia: {search_query}")
    try:
        results = search_wikipedia(search_query, max_results=3)
        for doc in results:
            if not pg_store.is_crawled(doc["url"]):
                new_docs.append(doc)
                pg_store.mark_crawled(doc["url"], doc["title"], "wikipedia")
                print(f"  ✅ Wiki: {doc['title']}")
            else:
                print(f"  ⏭️ Đã crawl: {doc['title']}")
    except Exception as e:
        print(f"  ❌ Wikipedia: {e}")

    # Google
    if has_google:
        print(f"[Crawl] Google: {search_query}")
        try:
            urls = do_google_search(search_query + " lịch sử Việt Nam", num_results=5)
            for url in urls:
                if pg_store.is_crawled(url):
                    continue
                result = scrape_page(url)
                if result:
                    new_docs.append(result)
                    pg_store.mark_crawled(url, result.get("title", ""), "web")
                    print(f"  ✅ Web: {result.get('title', '')[:50]}")
        except Exception as e:
            print(f"  ❌ Google: {e}")

    # Index vào PostgreSQL
    if new_docs:
        return pg_store.add_documents(new_docs)
    print("[Crawl] Không có dữ liệu mới")
    return 0


def _build_prompt(question: str, context: str, history: str) -> str:
    """Tạo prompt cho LLM."""
    prompt = f"""Bạn là một chuyên gia lịch sử Việt Nam uyên bác.

NHIỆM VỤ: Trả lời câu hỏi dựa trên tài liệu tham khảo được cung cấp.

HƯỚNG DẪN:
- Phân tích KỸ LƯỠNG tất cả tài liệu bên dưới, tìm mọi thông tin liên quan
- Tổng hợp thông tin từ NHIỀU tài liệu khác nhau để đưa ra câu trả lời đầy đủ
- Nếu tài liệu đề cập gián tiếp, hãy SUY LUẬN và kết nối thông tin
- Trả lời CHI TIẾT với các mốc thời gian, nhân vật, sự kiện cụ thể
- Trả lời bằng tiếng Việt, mạch lạc, dễ hiểu
- Nếu thực sự KHÔNG có bất kỳ thông tin nào liên quan, hãy nói rõ

TÀI LIỆU THAM KHẢO:
{context}
"""

    if history:
        prompt += f"""
LỊCH SỬ HỘI THOẠI GẦN ĐÂY:
{history}
"""

    prompt += f"""
CÂU HỎI: {question}

HÃY TRẢ LỜI CHI TIẾT VÀ CHÍNH XÁC:"""

    return prompt


def ask_pg(question: str, session_id: str = "default") -> dict:
    """Flow chính dùng PostgreSQL."""
    print(f"\n{'='*50}")
    print(f"[Question] {question}")

    # Bước 1: Query context từ PostgreSQL
    context, sources, results = pg_store.get_context(question, n_results=10)

    crawl_info = None

    # Bước 2: Nếu ít context → crawl
    if len(results) < 3:
        print("[Flow] Ít context → crawl bổ sung...")
        added = crawl_and_index(question)
        crawl_info = {"crawled": True, "new_chunks": added}
        if added > 0:
            context, sources, results = pg_store.get_context(question, n_results=10)

    # Bước 3: Lấy history từ PostgreSQL
    history_records = pg_store.get_chat_history(session_id, max_turns=3)
    history = ""
    for r in history_records:
        history += f"Người dùng: {r['user_message']}\nTrợ lý: {r['bot_response'][:300]}\n\n"

    # Bước 4: Gọi LLM
    prompt = _build_prompt(question, context, history)
    print(f"[LLM] Context: {len(context)} chars, Prompt: {len(prompt)} chars")
    answer = _call_llm(prompt)
    print(f"[LLM] → {answer[:150]}...")

    # Bước 5: Nếu thiếu info → crawl rồi hỏi lại
    if _answer_lacks_info(answer) and not crawl_info:
        print("[Flow] LLM thiếu info → crawl bổ sung...")
        added = crawl_and_index(question)
        crawl_info = {"crawled": True, "new_chunks": added}
        if added > 0:
            context, sources, results = pg_store.get_context(question, n_results=10)
            prompt = _build_prompt(question, context, "")
            answer = _call_llm(prompt)
            print(f"[LLM] Trả lời lần 2: {answer[:150]}...")

    # Bước 6: Lưu chat vào PostgreSQL
    pg_store.save_chat(session_id, question, answer, sources)

    return {
        "answer": answer,
        "sources": sources[:5],
        "context_used": len(sources) > 0,
        "crawl_info": crawl_info,
    }


def clear_history_pg(session_id: str = "default"):
    """Xóa lịch sử chat."""
    pg_store.clear_chat_history(session_id)


def get_stats():
    """Lấy thống kê database."""
    return pg_store.get_stats()