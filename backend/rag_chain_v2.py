"""
RAG Chain V2: Tích hợp flow đánh giá context → crawl nếu thiếu → index → trả lời.
"""
import sys
import os
import time

# Thêm tất cả thư mục cần thiết vào path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_COLLECTION_DIR = os.path.join(ROOT_DIR, "data_collection")
DATA_PROCESSING_DIR = os.path.join(ROOT_DIR, "data_processing")

for p in [ROOT_DIR, BACKEND_DIR, DATA_COLLECTION_DIR, DATA_PROCESSING_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import chromadb
from config import CHROMA_DB_PATH, COLLECTION_NAME, USE_GROQ, GEMINI_API_KEY
from context_evaluator import evaluate_context

# ============ LLM Setup ============
if USE_GROQ:
    from groq import Groq
    groq_key = os.getenv("GROQ_API_KEY")
    groq_client = Groq(api_key=groq_key)
    print("✅ Đã kết nối Groq API (llama-3.3-70b)")
else:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    print("✅ Đã kết nối Gemini API")

# ============ Session History ============
sessions = {}

# Từ khóa cho thấy LLM không tìm được thông tin
NO_INFO_KEYWORDS = [
    "không có thông tin", "không tìm thấy", "không chứa",
    "không đề cập", "không có dữ liệu", "không đủ thông tin",
    "xin lỗi, nhưng", "không có trong", "không được đề cập",
    "tài liệu không chứa", "chưa có thông tin", "không chứa thông tin",
    "không có thông tin cụ thể", "không có thông tin trực tiếp",
]


def _call_llm(prompt: str) -> str:
    """Gọi LLM với retry."""
    for attempt in range(3):
        try:
            if USE_GROQ:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Bạn là chuyên gia lịch sử Việt Nam. Hãy phân tích kỹ tài liệu được cung cấp và trả lời chi tiết, chính xác. Khi tài liệu có thông tin liên quan, hãy tổng hợp và suy luận để đưa ra câu trả lời đầy đủ nhất."},
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


def _get_collection():
    """Lấy collection mới nhất từ ChromaDB."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def _query_context(question: str, n_results: int = 10):
    """Query ChromaDB - lấy nhiều context hơn và lọc chất lượng."""
    collection = _get_collection()
    results = collection.query(query_texts=[question], n_results=n_results)

    if not results["documents"][0]:
        return "", [], results

    context_parts = []
    sources = []

    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    )):
        # Chỉ lấy chunk có similarity tốt (distance < 0.5)
        if dist > 0.5:
            continue

        source = meta.get("source", "Unknown")
        url = meta.get("url", "")
        if source not in sources:
            sources.append(source)
        # Lấy TOÀN BỘ nội dung chunk, không cắt
        context_parts.append(f"[Tài liệu {len(context_parts)+1} - {source}]:\n{doc}\n")
        print(f"  📄 Context {len(context_parts)}: {source} (dist={dist:.3f}) - {doc[:80]}...")

    context = "\n".join(context_parts)
    print(f"  📊 Tổng context: {len(context)} ký tự từ {len(context_parts)} chunks")
    return context, sources, results


def _answer_lacks_info(answer: str) -> bool:
    answer_lower = answer.lower()
    return any(kw in answer_lower for kw in NO_INFO_KEYWORDS)


def _extract_keywords(question: str) -> str:
    remove_words = [
        "bạn", "có", "biết", "gì", "về", "không", "cho", "tôi",
        "hãy", "kể", "nói", "là", "như", "thế", "nào", "ra", "sao",
        "được", "của", "và", "hay", "hoặc", "với", "trong", "này",
        "đó", "ở", "từ", "đến", "ạ", "vậy", "thì", "bàn", "đàm", "phán",
        "đó", "còn", "gọi", "diễn", "ai", "người", "nào", "vào",
    ]
    words = question.lower().replace("?", "").replace("!", "").replace(",", "").replace(">", "").split()
    keywords = [w for w in words if w not in remove_words and len(w) > 1]
    result = " ".join(keywords) if keywords else question
    print(f"[Keywords] '{question}' → '{result}'")
    return result


def _get_history(session_id: str, max_turns: int = 3) -> str:
    if session_id not in sessions:
        sessions[session_id] = []
    history = sessions[session_id]
    if not history:
        return ""
    recent = history[-max_turns:]
    formatted = ""
    for turn in recent:
        formatted += f"Người dùng: {turn['user']}\n"
        formatted += f"Trợ lý: {turn['bot'][:300]}\n\n"
    return formatted


def _clean_answer(answer: str) -> str:
    lines = answer.split('\n')
    clean_lines = []
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith('nguồn sử dụng') or stripped.startswith('nguồn tài liệu'):
            break
        clean_lines.append(line)
    while clean_lines and clean_lines[-1].strip() == '':
        clean_lines.pop()
    return '\n'.join(clean_lines)


def crawl_and_index(query: str) -> int:
    """Crawl Wikipedia + Google, index vào ChromaDB."""
    from wiki_crawler import search_wikipedia
    from google_search import google_search as do_google_search
    from google_search import scrape_page
    from source_manager import is_already_crawled, mark_as_crawled, is_trusted_source
    from dynamic_indexing import add_new_documents

    search_query = _extract_keywords(query)
    new_docs = []

    # 1. Wikipedia - tìm chính xác hơn
    print(f"[Crawl] Wikipedia: {search_query}")
    try:
        wiki_results = search_wikipedia(search_query, max_results=3)
        for doc in wiki_results:
            if not is_already_crawled(doc["url"]):
                new_docs.append(doc)
                mark_as_crawled(doc["url"], doc["title"], doc.get("source", "wikipedia"))
                print(f"  ✅ Wiki: {doc['title']}")
            else:
                print(f"  ⏭️ Đã crawl: {doc['title']}")
    except Exception as e:
        print(f"  ❌ Wikipedia: {e}")

    # 2. Google
    print(f"[Crawl] Google: {search_query}")
    try:
        urls = do_google_search(search_query + " lịch sử Việt Nam", num_results=5)
        print(f"  Tìm được {len(urls)} URLs")
        for url in urls:
            if is_already_crawled(url):
                continue
            if not is_trusted_source(url):
                continue
            result = scrape_page(url)
            if result:
                new_docs.append(result)
                mark_as_crawled(url, result.get("title", ""), result.get("source", "web"))
                print(f"  ✅ Web: {result.get('title', '')[:50]}")
    except Exception as e:
        print(f"  ❌ Google: {e}")

    # 3. Index
    if new_docs:
        try:
            added = add_new_documents(new_docs)
            print(f"[Index] Đã thêm {added} chunk mới")
            return added
        except Exception as e:
            print(f"  ❌ Index: {e}")
            return 0

    print("[Crawl] Không có dữ liệu mới")
    return 0


def _build_prompt(question: str, context: str, history: str) -> str:
    """Build prompt tối ưu cho LLM."""
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


def ask_v2(question: str, session_id: str = "default") -> dict:
    """Flow chính."""
    print(f"\n{'='*50}")
    print(f"[Question] {question}")

    # Bước 1: Query context (lấy 10 chunks thay vì 5)
    context, sources, search_results = _query_context(question, n_results=10)
    evaluation = evaluate_context(question, search_results)
    print(f"[Đánh giá] sufficient={evaluation['sufficient']}, "
          f"confidence={evaluation['confidence']}, chunks={evaluation['relevant_chunks']}")

    crawl_info = None

    # Bước 2: Crawl nếu context không đủ
    if not evaluation["sufficient"]:
        print(f"[Flow] Context không đủ → crawl...")
        added = crawl_and_index(question)
        crawl_info = {"crawled": True, "new_chunks": added, "reason": evaluation["reason"]}
        if added > 0:
            context, sources, search_results = _query_context(question, n_results=10)

    # Bước 3: Gọi LLM
    history = _get_history(session_id)
    prompt = _build_prompt(question, context, history)
    print(f"[LLM] Gọi LLM với {len(context)} ký tự context, {len(prompt)} ký tự prompt...")
    answer = _call_llm(prompt)
    clean_answer = _clean_answer(answer)
    print(f"[LLM] Trả lời: {clean_answer[:150]}...")

    # Bước 4: Nếu LLM thiếu info → crawl rồi hỏi lại
    if _answer_lacks_info(clean_answer) and not crawl_info:
        print(f"[Flow] LLM thiếu thông tin → crawl bổ sung...")
        added = crawl_and_index(question)
        crawl_info = {"crawled": True, "new_chunks": added, "reason": "LLM thieu thong tin"}

        if added > 0:
            print(f"[Flow] Đã thêm {added} chunks → hỏi lại...")
            context, sources, search_results = _query_context(question, n_results=10)
            prompt = _build_prompt(question, context, "")
            answer = _call_llm(prompt)
            clean_answer = _clean_answer(answer)
            print(f"[LLM] Trả lời lần 2: {clean_answer[:150]}...")

    # Lưu history
    if session_id not in sessions:
        sessions[session_id] = []
    sessions[session_id].append({'user': question, 'bot': clean_answer})

    result = {
        'answer': clean_answer,
        'sources': sources[:5],
        'context_used': len(sources) > 0,
        'evaluation': evaluation,
    }
    if crawl_info:
        result['crawl_info'] = crawl_info

    return result


def clear_history_v2(session_id: str = "default"):
    if session_id in sessions:
        sessions[session_id] = []