"""
RAG Engine: Tìm kiếm và trả lời câu hỏi lịch sử Việt Nam
Sử dụng ChromaDB + Groq LLM.
Hỗ trợ: hybrid search (embedding + keyword), chunk liên tiếp, follow-up context.
"""

import os
import sys
import re
from dotenv import load_dotenv

# Thêm path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "data_processing"))
sys.path.insert(0, ROOT_DIR)

# Load biến môi trường - thử nhiều cách
ENV_PATH = os.path.join(ROOT_DIR, ".env")
print(f"[RAG] .env path: {ENV_PATH}")
print(f"[RAG] .env exists: {os.path.exists(ENV_PATH)}")

load_dotenv(ENV_PATH, override=True)

from indexing import search, get_stats, get_collection
from groq import Groq

# ======================== CẤU HÌNH ========================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

MAX_KEYWORD_CHUNKS = 15       # Tối đa chunks từ keyword search
MAX_TOTAL_CHUNKS = 20         # Tối đa chunks tổng cộng
MAX_CONTEXT_CHARS = 8000      # Tối đa ký tự context gửi LLM

# Fallback: đọc trực tiếp từ .env nếu load_dotenv thất bại
if not GROQ_API_KEY and os.path.exists(ENV_PATH):
    print("[RAG] ⚠️ load_dotenv không load được GROQ_API_KEY, thử đọc trực tiếp...")
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GROQ_API_KEY="):
                    GROQ_API_KEY = line.split("=", 1)[1].strip()
                    break
    except Exception as e:
        print(f"[RAG] ❌ Lỗi đọc .env: {e}")

groq_client = None
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print(f"[RAG] ✅ Groq client khởi tạo thành công (key: {GROQ_API_KEY[:10]}...)")
    except Exception as e:
        print(f"[RAG] ❌ Lỗi khởi tạo Groq client: {e}")
else:
    print("[RAG] ❌ GROQ_API_KEY trống! Chatbot sẽ không gọi được AI.")

# ======================== SESSION STATE ========================
_chat_histories = {}
_session_contexts = {}
_session_topics = {}

# ======================== SYSTEM PROMPT ========================
SYSTEM_PROMPT = """Bạn là một chuyên gia lịch sử Việt Nam. Nhiệm vụ của bạn là trả lời các câu hỏi về lịch sử Việt Nam dựa trên tài liệu được cung cấp.

QUY TẮC BẮT BUỘC:
1. CHỈ trả lời dựa trên thông tin có trong phần "TÀI LIỆU THAM KHẢO". KHÔNG sử dụng kiến thức bên ngoài.
2. Trả lời bằng tiếng Việt, rõ ràng, mạch lạc, có cấu trúc logic.
3. Nếu tài liệu không đủ thông tin, hãy nói rõ phần nào thiếu.
4. TUYỆT ĐỐI KHÔNG bịa đặt thông tin không có trong tài liệu.
5. Trình bày có tiêu đề, gạch đầu dòng, đánh số khi cần.
6. Trình bày theo thứ tự thời gian nếu có nhiều sự kiện.
7. Loại bỏ các ký hiệu wiki: ===, ==, ----, #, [[, ]].
8. Trả lời ĐẦY ĐỦ: bối cảnh, diễn biến, kết quả, ý nghĩa (nếu tài liệu có).
9. Khi tóm tắt sự kiện: thời gian, địa điểm, nhân vật chính, diễn biến, kết quả.
"""

# ======================== FOLLOW-UP DETECTION ========================
FOLLOW_UP_INDICATORS = [
    "này", "đó", "trên", "trận đánh này", "sự kiện này", "chiến dịch này",
    "nó", "cuộc chiến này", "giai đoạn này", "thời kỳ này",
    "chi tiết hơn", "cụ thể hơn", "giải thích thêm", "nói thêm",
    "tiếp tục", "còn gì nữa", "ý nghĩa của nó", "kết quả của nó",
    "bổ sung", "mở rộng", "phân tích thêm",
    "vậy thì", "thế còn", "ngoài ra",
]

# ======================== KEYWORD → SOURCE MAPPING ========================
# Giúp tìm đúng file nguồn khi embedding search không chính xác
KEYWORD_SOURCE_MAP = {
    # Hà Nội 12 ngày đêm
    "12 ngày đêm": "Hà Nội 12 ngày đêm.txt",
    "linebacker": "Hà Nội 12 ngày đêm.txt",
    "điện biên phủ trên không": "Hà Nội 12 ngày đêm.txt",
    "b-52": "Hà Nội 12 ngày đêm.txt",
    "b52": "Hà Nội 12 ngày đêm.txt",
    "pháo đài bay": "Hà Nội 12 ngày đêm.txt",
    "khâm thiên": "Hà Nội 12 ngày đêm.txt",
    "bạch mai": "Hà Nội 12 ngày đêm.txt",
    "phạm tuân": "Hà Nội 12 ngày đêm.txt",
    "ném bom hà nội": "Hà Nội 12 ngày đêm.txt",
    "hà nội 12": "Hà Nội 12 ngày đêm.txt",

    # Thành cổ Quảng Trị
    "thành cổ quảng trị": "Thành cổ Quảng Trị và Hiệp định Paris.txt",
    "81 ngày đêm": "Thành cổ Quảng Trị và Hiệp định Paris.txt",
    "quảng trị 1972": "Thành cổ Quảng Trị và Hiệp định Paris.txt",
    "sông thạch hãn": "Thành cổ Quảng Trị và Hiệp định Paris.txt",
    "mùa hè đỏ lửa": "Thành cổ Quảng Trị và Hiệp định Paris.txt",
    "hiệp định paris": "Thành cổ Quảng Trị và Hiệp định Paris.txt",
    "lam sơn 72": "Thành cổ Quảng Trị và Hiệp định Paris.txt",

    # Điện Biên Phủ 1954
    "điện biên phủ 1954": "CHIẾN DỊCH ĐIỆN BIÊN PHỦ (1954).txt",
    "chiến dịch điện biên phủ": "CHIẾN DỊCH ĐIỆN BIÊN PHỦ (1954).txt",
    "đờ cát": "CHIẾN DỊCH ĐIỆN BIÊN PHỦ (1954).txt",
    "de castries": "CHIẾN DỊCH ĐIỆN BIÊN PHỦ (1954).txt",
    "mường thanh": "CHIẾN DỊCH ĐIỆN BIÊN PHỦ (1954).txt",
    "điện biên phủ": "CHIẾN DỊCH ĐIỆN BIÊN PHỦ (1954).txt",

    # Bạch Đằng
    "bạch đằng": "CHIẾN THẮNG BẠCH ĐẰNG NĂM 938.txt",
    "ngô quyền": "CHIẾN THẮNG BẠCH ĐẰNG NĂM 938.txt",
    "938": "CHIẾN THẮNG BẠCH ĐẰNG NĂM 938.txt",

    # Hai Bà Trưng
    "hai bà trưng": "KHỞI NGHĨA HAI BÀ TRƯNG.txt",
    "trưng trắc": "KHỞI NGHĨA HAI BÀ TRƯNG.txt",
    "trưng nhị": "KHỞI NGHĨA HAI BÀ TRƯNG.txt",

    # Cách mạng Tháng Tám
    "cách mạng tháng tám": "CÁCH MẠNG THÁNG TÁM NĂM 1945.txt",
    "tháng tám 1945": "CÁCH MẠNG THÁNG TÁM NĂM 1945.txt",
    "cách mạng tháng 8": "CÁCH MẠNG THÁNG TÁM NĂM 1945.txt",

    # Kháng chiến chống Mỹ
    "kháng chiến chống mỹ": "KHÁNG CHIẾN CHỐNG MỸ CỨU NƯỚC (1954 - 1975).txt",
    "chống mỹ cứu nước": "KHÁNG CHIẾN CHỐNG MỸ CỨU NƯỚC (1954 - 1975).txt",

    # Nhà Lý
    "nhà lý": "TRIỀU ĐẠI NHÀ LÝ (1009 - 1225).txt",
    "lý công uẩn": "TRIỀU ĐẠI NHÀ LÝ (1009 - 1225).txt",
    "lý thường kiệt": "TRIỀU ĐẠI NHÀ LÝ (1009 - 1225).txt",
    "triều lý": "TRIỀU ĐẠI NHÀ LÝ (1009 - 1225).txt",

    # Nhà Trần
    "nhà trần": "TRIỀU ĐẠI NHÀ TRẦN (1226 - 1400).txt",
    "trần hưng đạo": "TRIỀU ĐẠI NHÀ TRẦN (1226 - 1400).txt",
    "nguyên mông": "TRIỀU ĐẠI NHÀ TRẦN (1226 - 1400).txt",
    "chống nguyên mông": "TRIỀU ĐẠI NHÀ TRẦN (1226 - 1400).txt",
    "triều trần": "TRIỀU ĐẠI NHÀ TRẦN (1226 - 1400).txt",

    # Wiki sources
    "bắc thuộc": "wiki_Bắc_thuộc.txt",
    "chiến dịch biên giới": "wiki_Chiến_dịch_Biên_giới.txt",
    "đánh tống": "wiki_Chiến_dịch_đánh_Tống_10751076.txt",
    "lý thường kiệt đánh tống": "wiki_Chiến_dịch_đánh_Tống_10751076.txt",
    "biên giới campuchia": "wiki_Chiến_tranh_biên_giới_Việt_Nam__Campuchia.txt",
    "pol pot": "wiki_Chiến_tranh_biên_giới_Việt_Nam__Campuchia.txt",
    "biên giới 1979": "wiki_Chiến_tranh_biên_giới_Việt__Trung_1979.txt",
    "chiến tranh biên giới": "wiki_Chiến_tranh_biên_giới_Việt__Trung_1979.txt",
    "chiến tranh việt nam": "wiki_Chiến_tranh_Việt_Nam.txt",
    "chiến tranh đông dương": "wiki_Chiến_tranh_Đông_Dương.txt",
    "lê duẩn": "wiki_Lê_Duẩn.txt",
    "nhà hậu lê": "wiki_Nhà_Hậu_Lê.txt",
    "lê trung hưng": "wiki_Nhà_Lê_trung_hưng.txt",
    "quân đội nhân dân": "wiki_Quân_đội_nhân_dân_Việt_Nam.txt",
    "thời bao cấp": "wiki_Thời_bao_cấp.txt",
    "bao cấp": "wiki_Thời_bao_cấp.txt",
}


# ======================== HELPER FUNCTIONS ========================

def _is_follow_up_question(question: str) -> bool:
    """Kiểm tra câu hỏi có phải follow-up không."""
    question_lower = question.lower().strip()
    for indicator in FOLLOW_UP_INDICATORS:
        if indicator in question_lower:
            return True
    if len(question_lower) < 25:
        return True
    return False


def _is_topic_change(question: str, current_topic: str) -> bool:
    """Kiểm tra người dùng chuyển sang chủ đề mới."""
    if not current_topic:
        return True
    question_lower = question.lower().strip()
    topic_lower = current_topic.lower().strip()
    for keyword in KEYWORD_SOURCE_MAP.keys():
        if keyword in question_lower and keyword not in topic_lower:
            return True
    return False


def _extract_topic(question: str) -> str:
    """Trích xuất chủ đề chính từ câu hỏi."""
    question_clean = question.lower().strip()
    remove_words = [
        "hãy", "cho tôi biết", "tóm tắt", "giải thích", "kể về",
        "nói về", "trình bày", "phân tích", "mô tả", "liệt kê",
        "là gì", "như thế nào", "ra sao", "tại sao", "vì sao",
        "có ý nghĩa gì", "diễn ra thế nào", "diễn biến",
        "chi tiết", "cụ thể", "đầy đủ", "ngắn gọn",
        "lại", "về", "của", "trong", "với", "thế còn", "thì sao",
    ]
    for word in remove_words:
        question_clean = question_clean.replace(word, "")
    return question_clean.strip()


def _call_groq(messages: list) -> str:
    """Gọi Groq API."""
    if not groq_client:
        print("[RAG] ❌ groq_client is None → không thể gọi API!")
        return None
    try:
        print(f"[RAG] 🤖 Đang gọi Groq API (model: llama-3.3-70b-versatile, messages: {len(messages)})...")
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=4096,
            top_p=0.9,
        )
        answer = response.choices[0].message.content
        print(f"[RAG] ✅ Groq trả lời thành công ({len(answer)} ký tự)")
        return answer
    except Exception as e:
        print(f"[RAG] ❌ Lỗi Groq API: {e}")
        return None


# ======================== HYBRID SEARCH ========================

def _find_matching_sources(question: str) -> list:
    """
    Tìm nguồn file phù hợp dựa trên keyword mapping.
    Sắp xếp theo độ dài keyword (dài hơn = chính xác hơn = ưu tiên hơn).
    """
    question_lower = question.lower().strip()
    matched_sources = {}

    # Sắp xếp keywords theo độ dài giảm dần (match dài trước)
    sorted_keywords = sorted(KEYWORD_SOURCE_MAP.keys(), key=len, reverse=True)

    for keyword in sorted_keywords:
        if keyword in question_lower:
            source = KEYWORD_SOURCE_MAP[keyword]
            if source not in matched_sources:
                matched_sources[source] = len(keyword)  # Lưu độ dài keyword

    # Sắp xếp sources theo độ dài keyword match (keyword dài = chính xác hơn)
    sorted_sources = sorted(matched_sources.items(), key=lambda x: x[1], reverse=True)
    return [s[0] for s in sorted_sources]


def _keyword_search_by_source(source_filename: str) -> list:
    """
    Lấy chunks từ một nguồn file cụ thể trong ChromaDB.
    Giới hạn tối đa MAX_KEYWORD_CHUNKS chunks.
    """
    try:
        collection = get_collection()
        results = collection.get(
            where={"source": {"$eq": source_filename}},
            include=["documents", "metadatas"]
        )

        if not results or not results["documents"]:
            print(f"  ⚠️ Không tìm thấy chunks cho source: {source_filename}")
            return []

        chunks = []
        seen = set()
        for doc, meta in zip(results["documents"], results["metadatas"]):
            # Loại bỏ trùng lặp
            content_hash = doc[:200]
            if content_hash in seen:
                continue
            seen.add(content_hash)

            chunks.append({
                "content": doc,
                "metadata": meta,
                "score": 0.95,
                "is_keyword_match": True
            })

        # Sắp xếp theo chunk_index
        chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
        
        # Giới hạn số chunks
        if len(chunks) > MAX_KEYWORD_CHUNKS:
            print(f"  ⚠️ {source_filename}: {len(chunks)} chunks → cắt còn {MAX_KEYWORD_CHUNKS}")
            chunks = chunks[:MAX_KEYWORD_CHUNKS]
        
        print(f"  📄 {source_filename}: {len(chunks)} chunks (keyword match)")
        return chunks

    except Exception as e:
        print(f"⚠️ Lỗi keyword search cho {source_filename}: {e}")
        return []


def _hybrid_search(question: str, top_k: int = 8) -> list:
    """
    Hybrid search: Keyword search (ưu tiên) + Embedding search (bổ sung).
    Có giới hạn tổng số chunks để tránh vượt token limit.
    """
    all_chunks = {}

    # === BƯỚC 1: Keyword search ===
    matched_sources = _find_matching_sources(question)
    print(f"🔑 Keyword match: {matched_sources if matched_sources else 'Không tìm thấy'}")

    keyword_chunk_count = 0
    for source in matched_sources:
        source_chunks = _keyword_search_by_source(source)
        for chunk in source_chunks:
            chunk_index = chunk["metadata"].get("chunk_index", 0)
            key = (source, chunk_index)
            if key not in all_chunks:
                all_chunks[key] = chunk
                keyword_chunk_count += 1
        
        # Dừng nếu đã đủ chunks
        if keyword_chunk_count >= MAX_KEYWORD_CHUNKS:
            break

    # === BƯỚC 2: Embedding search ===
    embedding_results = search(question, top_k=top_k)
    print(f"🔍 Embedding search: {len(embedding_results)} chunks")

    embedding_chunk_count = 0
    for r in embedding_results:
        content = r["content"].strip()
        metadata = r.get("metadata", {})
        source = metadata.get("source", "unknown")
        chunk_index = metadata.get("chunk_index", -1)
        score = r.get("score", 0)

        key = (source, chunk_index)
        if key not in all_chunks:
            all_chunks[key] = {
                "content": content,
                "metadata": metadata,
                "score": score,
                "is_keyword_match": False
            }
            embedding_chunk_count += 1

    # === BƯỚC 3: Chọn chunks cuối cùng ===
    if matched_sources:
        keyword_chunks = [v for k, v in all_chunks.items() if k[0] in matched_sources]
        other_chunks = [v for k, v in all_chunks.items() if k[0] not in matched_sources]
        other_chunks.sort(key=lambda x: x["score"], reverse=True)
        final_chunks = keyword_chunks + other_chunks[:3]
    else:
        final_chunks = list(all_chunks.values())

    # Giới hạn tổng số chunks
    if len(final_chunks) > MAX_TOTAL_CHUNKS:
        print(f"  ⚠️ Cắt từ {len(final_chunks)} → {MAX_TOTAL_CHUNKS} chunks")
        final_chunks = final_chunks[:MAX_TOTAL_CHUNKS]

    # Sắp xếp theo source rồi chunk_index
    final_chunks.sort(key=lambda x: (
        x["metadata"].get("source", ""),
        x["metadata"].get("chunk_index", 0)
    ))

    print(f"📊 Tổng: {len(final_chunks)} chunks (keyword: {keyword_chunk_count}, embedding: {embedding_chunk_count})")
    return final_chunks


# ======================== PUBLIC API ========================

def retrieve_context(query: str, top_k: int = 8) -> str:
    """Tìm kiếm context liên quan từ ChromaDB (hybrid search)."""
    results = _hybrid_search(query, top_k=top_k)
    if not results:
        return ""

    source_groups = {}
    for r in results:
        source = r["metadata"].get("source", "unknown")
        if source not in source_groups:
            source_groups[source] = []
        source_groups[source].append(r)

    context_parts = []
    for source, chunks in source_groups.items():
        chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
        source_content = f"[Nguồn: {source}]\n"
        for chunk in chunks:
            source_content += chunk["content"].strip() + "\n\n"
        context_parts.append(source_content.strip())

    return "\n\n---\n\n".join(context_parts)


def get_database_info() -> dict:
    """Lấy thông tin về database."""
    return get_stats()


def ask_pg(question: str, session_id: str = "default") -> dict:
    """
    Trả lời câu hỏi lịch sử: ChromaDB hybrid search + Groq AI.
    """
    # --- Session state ---
    current_topic = _session_topics.get(session_id, "")
    current_context = _session_contexts.get(session_id, "")
    current_sources = _session_contexts.get(f"{session_id}_sources", [])

    # --- Follow-up detection ---
    is_follow_up = _is_follow_up_question(question)
    is_new_topic = _is_topic_change(question, current_topic)
    use_previous_context = False

    if current_context and is_follow_up and not is_new_topic:
        use_previous_context = True
        print(f"🔄 Follow-up: Giữ context về '{current_topic}'")
    else:
        print(f"🔍 Chủ đề mới: Tìm kiếm cho '{question}'")

    # --- Tìm kiếm hoặc dùng context cũ ---
    if use_previous_context:
        context = current_context
        sources = current_sources
        sufficient = True
        confidence = "Cao"
    else:
        results = _hybrid_search(question, top_k=8)

        if not results:
            return {
                "answer": "Xin lỗi, tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu.",
                "sources": [],
                "crawl_info": None,
                "evaluation": {"sufficient": False, "confidence": "Thấp"}
            }

        # Nhóm theo source, sắp xếp theo chunk_index
        source_groups = {}
        sources = []
        for r in results:
            source = r["metadata"].get("source", "unknown")
            if source not in source_groups:
                source_groups[source] = []
                if source not in sources:
                    sources.append(source)
            source_groups[source].append(r)

        context_parts = []
        for source, chunks in source_groups.items():
            chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))

            seen = set()
            unique_chunks = []
            for chunk in chunks:
                content_hash = chunk["content"][:200]
                if content_hash not in seen:
                    seen.add(content_hash)
                    unique_chunks.append(chunk)

            source_text = f"[Nguồn: {source}]\n"
            for chunk in unique_chunks:
                source_text += chunk["content"].strip() + "\n\n"
            context_parts.append(source_text.strip())

        context = "\n\n---\n\n".join(context_parts)

        # === CẮT CONTEXT NẾU QUÁ DÀI ===
        if len(context) > MAX_CONTEXT_CHARS:
            print(f"  ✂️ Context quá dài ({len(context)} chars) → cắt còn {MAX_CONTEXT_CHARS} chars")
            context = context[:MAX_CONTEXT_CHARS]
            # Cắt tại vị trí cuối câu gần nhất
            last_period = context.rfind(".")
            last_newline = context.rfind("\n")
            cut_pos = max(last_period, last_newline)
            if cut_pos > MAX_CONTEXT_CHARS * 0.7:
                context = context[:cut_pos + 1]
            context += "\n\n[... tài liệu được rút gọn do giới hạn độ dài ...]"

        # Đánh giá
        keyword_count = sum(1 for r in results if r.get("is_keyword_match", False))
        if keyword_count > 0:
            sufficient = True
            confidence = "Cao"
        else:
            scores = [r["score"] for r in results]
            avg_score = sum(scores) / len(scores) if scores else 0
            sufficient = avg_score > 0.3
            confidence = "Cao" if avg_score > 0.6 else ("Trung bình" if avg_score > 0.3 else "Thấp")

        # Cập nhật session
        _session_topics[session_id] = _extract_topic(question)
        _session_contexts[session_id] = context
        _session_contexts[f"{session_id}_sources"] = sources

    # --- Tạo messages cho Groq ---
    history = _chat_histories.get(session_id, [])
    recent_history = history[-2:] if len(history) > 2 else history

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for h in recent_history:
        # Rút gọn lịch sử để tiết kiệm token
        short_answer = h["answer"][:500] + "..." if len(h["answer"]) > 500 else h["answer"]
        messages.append({"role": "user", "content": h["question"]})
        messages.append({"role": "assistant", "content": short_answer})

    context_note = ""
    if use_previous_context:
        context_note = "\n\n⚠️ QUAN TRỌNG: Người dùng đang hỏi tiếp về chủ đề trước. Trả lời dựa trên CÙNG tài liệu."

    user_message = f"""TÀI LIỆU THAM KHẢO (CHỈ dựa trên nội dung bên dưới để trả lời):

{context}
{context_note}

CÂU HỎI:
{question}

YÊU CẦU:
- Trả lời ĐẦY ĐỦ dựa trên tài liệu tham khảo.
- Trình bày có cấu trúc: tiêu đề, gạch đầu dòng, đánh số.
- Bao gồm: bối cảnh, diễn biến, kết quả, ý nghĩa (nếu tài liệu có).
- Nếu thiếu thông tin → nói rõ.
- KHÔNG thêm thông tin ngoài tài liệu."""

    messages.append({"role": "user", "content": user_message})

    # --- Ước tính token ---
    total_chars = sum(len(m["content"]) for m in messages)
    estimated_tokens = total_chars // 3
    print(f"[RAG] Gọi Groq: {len(messages)} messages, ~{estimated_tokens} tokens (context: {len(context)} chars)")
    
    if estimated_tokens > 10000:
        print(f"[RAG] ⚠️ Token quá cao ({estimated_tokens}), cắt context thêm...")
        # Cắt context mạnh hơn
        max_ctx = MAX_CONTEXT_CHARS // 2
        context = context[:max_ctx]
        last_cut = max(context.rfind("."), context.rfind("\n"))
        if last_cut > max_ctx * 0.5:
            context = context[:last_cut + 1]
        context += "\n\n[... tài liệu được rút gọn ...]"
        
        # Rebuild user message
        messages[-1] = {"role": "user", "content": f"""TÀI LIỆU THAM KHẢO:

{context}

CÂU HỎI: {question}

Trả lời đầy đủ, có cấu trúc, dựa trên tài liệu. KHÔNG bịa đặt."""}
        
        total_chars = sum(len(m["content"]) for m in messages)
        estimated_tokens = total_chars // 3
        print(f"[RAG] Sau cắt: ~{estimated_tokens} tokens")

    # --- Gọi Groq ---
    answer = _call_groq(messages)

    if not answer:
        print("[RAG] ⚠️ Groq không trả lời → dùng fallback (raw context)")
        clean_context = context
        for pattern in ["=====", "====", "===", "==", "----", "[[", "]]", "##", "# "]:
            clean_context = clean_context.replace(pattern, "")
        lines = [line.strip() for line in clean_context.split("\n") if line.strip()]
        clean_context = "\n".join(lines)
        answer = f"Dựa trên tài liệu lịch sử:\n\n{clean_context}"

    # --- Lưu lịch sử ---
    if session_id not in _chat_histories:
        _chat_histories[session_id] = []
    _chat_histories[session_id].append({
        "question": question,
        "answer": answer
    })

    return {
        "answer": answer,
        "sources": sources,
        "crawl_info": None,
        "evaluation": {
            "sufficient": sufficient,
            "confidence": confidence
        }
    }


def clear_history_pg(session_id: str = "default"):
    """Xóa lịch sử chat và context của một session."""
    if session_id in _chat_histories:
        _chat_histories[session_id] = []
    if session_id in _session_contexts:
        del _session_contexts[session_id]
    if f"{session_id}_sources" in _session_contexts:
        del _session_contexts[f"{session_id}_sources"]
    if session_id in _session_topics:
        del _session_topics[session_id]