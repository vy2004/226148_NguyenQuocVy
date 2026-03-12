"""
RAG Engine: Tìm kiếm và trả lời câu hỏi lịch sử Việt Nam
Sử dụng ChromaDB (embedding search) + Groq LLM + Gemini fallback.
"""

import os
import sys
import re
import tempfile
import unicodedata
from collections import Counter
from dotenv import load_dotenv

try:
    from backend.wiki_crawler import wiki_search_and_save
except ImportError:
    try:
        from wiki_crawler import wiki_search_and_save
    except ImportError:
        wiki_search_and_save = None
        print("[RAG] ⚠️ wiki_crawler module not found, auto-crawl disabled")

# Thêm path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "data_processing"))
sys.path.insert(0, ROOT_DIR)

# Load biến môi trường
ENV_PATH = os.path.join(ROOT_DIR, ".env")
print(f"[RAG] .env path: {ENV_PATH}")
print(f"[RAG] .env exists: {os.path.exists(ENV_PATH)}")

load_dotenv(ENV_PATH, override=True)

from indexing import search, get_stats, get_collection, create_vector_database
from loader import load_pdf_file
from chunking import chunk_documents
from groq import Groq
import google.generativeai as genai

# ======================== CẤU HÌNH ========================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Danh sách model Gemini dự phòng (thử lần lượt khi model chính bị quota)
GEMINI_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

MAX_TOTAL_CHUNKS = 20
MAX_CONTEXT_CHARS = 20000
MAX_HISTORY_TURNS = 2

# Fallback: đọc trực tiếp từ .env nếu load_dotenv thất bại
if not GROQ_API_KEY and os.path.exists(ENV_PATH):
    print("[RAG] ⚠️ load_dotenv không load được GROQ_API_KEY, thử đọc trực tiếp...")
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GROQ_API_KEY="):
                    GROQ_API_KEY = line.split("=", 1)[1].strip()
                elif line.startswith("GEMINI_API_KEY="):
                    GEMINI_API_KEY = line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"[RAG] ❌ Lỗi đọc .env: {e}")

# Log trạng thái keys
if GROQ_API_KEY:
    print(f"[RAG] ✅ GROQ_API_KEY loaded (key: {GROQ_API_KEY[:10]}...)")
else:
    print("[RAG] ⚠️ GROQ_API_KEY trống!")

if GEMINI_API_KEY:
    print(f"[RAG] ✅ GEMINI_API_KEY loaded (key: {GEMINI_API_KEY[:10]}...)")
else:
    print("[RAG] ⚠️ GEMINI_API_KEY trống! Fallback Gemini sẽ không hoạt động.")

# ======================== SESSION STATE ========================
_chat_histories = {}
_session_contexts = {}
_session_topics = {}
_source_cache = None
_last_llm_error = ""

SOURCE_QUERY_ALIASES = {
    "12 ngay dem": "dien bien phu tren khong",
    "ha noi 12 ngay dem": "dien bien phu tren khong",
    "linebacker ii": "dien bien phu tren khong",
}

# ======================== SYSTEM PROMPT ========================
SYSTEM_PROMPT = """Bạn là một chuyên gia lịch sử Việt Nam. Nhiệm vụ của bạn là trả lời các câu hỏi về lịch sử Việt Nam dựa trên tài liệu được cung cấp.

QUY TẮC BẮT BUỘC:
1. CHỈ trả lời dựa trên thông tin có trong phần "TÀI LIỆU THAM KHẢO". KHÔNG sử dụng kiến thức bên ngoài.
2. Trả lời bằng tiếng Việt, rõ ràng, mạch lạc.
3. TUYỆT ĐỐI KHÔNG bịa đặt thông tin không có trong tài liệu.
4. Nếu tài liệu không đủ thông tin, hãy nói rõ phần nào thiếu.

QUY TẮC VỀ ĐỘ DÀI VÀ HÌNH THỨC TRẢ LỜI:
- **Câu hỏi cụ thể** (hỏi năm, ngày, tên, địa điểm, con số...): Trả lời NGẮN GỌN, đi thẳng vào đáp án. KHÔNG thêm bối cảnh, diễn biến, ý nghĩa khi không được hỏi.
- **Câu hỏi yêu cầu chi tiết** (có từ: "trình bày", "nêu diễn biến", "phân tích", "giải thích", "kể về", "tóm tắt sự kiện", "cho biết chi tiết", "mô tả"...): Trả lời ĐẦY ĐỦ, có cấu trúc, trình bày theo thời gian nếu có nhiều sự kiện.
- **Câu hỏi mở** (ví dụ: "Trận Điện Biên Phủ là gì?"): Trả lời vừa đủ, tóm tắt ngắn gọn các thông tin chính, KHÔNG lan man.

VÍ DỤ:
- Hỏi: "Chủ tịch Hồ Chí Minh sinh ngày tháng năm nào?" → "Chủ tịch Hồ Chí Minh sinh ngày 19 tháng 5 năm 1890."
- Hỏi: "Trận Điện Biên Phủ diễn ra năm nào?" → "Trận Điện Biên Phủ diễn ra năm 1954."
- Hỏi: "Hãy trình bày diễn biến trận Điện Biên Phủ" → Trả lời chi tiết theo các đợt tấn công, mốc thời gian, nhân vật...
"""

# ======================== FOLLOW-UP DETECTION ========================
# Indicators cả có dấu và không dấu để match cả 2 trường hợp
FOLLOW_UP_INDICATORS = [
    "trận đánh này", "tran danh nay",
    "sự kiện này", "su kien nay",
    "chiến dịch này", "chien dich nay",
    "cuộc chiến này", "cuoc chien nay",
    "giai đoạn này", "giai doan nay",
    "thời kỳ này", "thoi ky nay",
    "chi tiết hơn", "chi tiet hon",
    "cụ thể hơn", "cu the hon",
    "giải thích thêm", "giai thich them",
    "nói thêm", "noi them",
    "tiếp tục", "tiep tuc",
    "còn gì nữa", "con gi nua",
    "ý nghĩa của nó", "y nghia cua no",
    "kết quả của nó", "ket qua cua no",
    "bổ sung", "bo sung",
    "mở rộng", "mo rong",
    "phân tích thêm", "phan tich them",
    "vậy thì", "vay thi",
    "thế còn", "the con",
    "ngoài ra", "ngoai ra",
    "người này", "nguoi nay",
    "ông ấy", "ong ay",
    "bà ấy", "ba ay",
    "vị này", "vi nay",
    "cuộc khởi nghĩa này", "cuoc khoi nghia nay",
    "hiệp định này", "hiep dinh nay",
    "trận này", "tran nay",
    "kể thêm", "ke them",
    "nói rõ hơn", "noi ro hon",
    "diễn biến của nó", "dien bien cua no",
]


# ======================== HELPER FUNCTIONS ========================

def _remove_diacritics(text: str) -> str:
    """Bỏ dấu tiếng Việt (giữ nguyên chữ đ → d)."""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")


def _is_follow_up_question(question: str) -> bool:
    """Kiểm tra câu hỏi có phải follow-up không."""
    question_lower = question.lower().strip()
    question_no_accent = _remove_diacritics(question_lower)

    # Kiểm tra các indicator cụ thể (cả có dấu và không dấu)
    for indicator in FOLLOW_UP_INDICATORS:
        if indicator in question_lower or indicator in question_no_accent:
            return True

    # Câu hỏi quá ngắn (< 30 ký tự) và không chứa danh từ riêng → follow-up
    # VD: "ngày mấy", "ở đâu", "kết quả là gì", "ông mất năm nào"
    if len(question_lower) < 30:
        # Kiểm tra cả có dấu và không dấu
        has_proper_noun = bool(re.search(
            r'(hồ chí minh|ho chi minh|điện biên|dien bien|bạch đằng|bach dang'
            r'|hai bà trưng|hai ba trung|ngô quyền|ngo quyen|quảng trị|quang tri'
            r'|việt trung|viet trung|việt nam|viet nam|campuchia|pháp|phap'
            r'|mỹ|my|mĩ|mi|giơnevo|gionevo|paris|sài gòn|sai gon|hà nội|ha noi'
            r'|tây nam|tay nam|nhà lý|nha ly|nhà trần|nha tran|nhà lê|nha le)',
            question_lower + " " + question_no_accent
        ))
        if not has_proper_noun:
            return True

    return False


def _extract_topic(question: str) -> str:
    """Trích xuất chủ đề chính từ câu hỏi (bỏ từ hỏi/lệnh, giữ danh từ chủ đề)."""
    question_clean = question.lower().strip()
    # Bỏ dấu câu
    question_clean = re.sub(r'[?!.,;:]', '', question_clean)

    # Bỏ các cụm từ hỏi/lệnh phổ biến (bao gồm cả không dấu)
    # LƯU Ý: KHÔNG bỏ "diễn biến"/"dien bien" vì trùng với "Điện Biên" (địa danh)
    remove_phrases = [
        "hãy", "hay",
        "cho tôi biết", "cho toi biet", "cho biết", "cho biet",
        "tóm tắt", "tom tat", "giải thích", "giai thich",
        "kể về", "ke ve", "kể lại", "ke lai",
        "nói về", "noi ve", "trình bày", "trinh bay",
        "phân tích", "phan tich", "mô tả", "mo ta", "liệt kê", "liet ke",
        "là gì", "la gi", "là ai", "la ai",
        "như thế nào", "nhu the nao", "ra sao",
        "tại sao", "tai sao", "vì sao", "vi sao",
        "có ý nghĩa gì", "co y nghia gi",
        "diễn ra thế nào", "dien ra the nao",
        "chi tiết", "chi tiet", "cụ thể", "cu the",
        "đầy đủ", "day du", "ngắn gọn", "ngan gon",
        "thế còn", "the con", "thì sao", "thi sao",
        "sinh ngày", "sinh ngay", "ngày mấy", "ngay may",
        "năm nào", "nam nao", "khi nào", "khi nao",
        "ở đâu", "o dau", "bao giờ", "bao gio",
        "mất ngày nào", "mat ngay nao",
    ]
    for phrase in remove_phrases:
        question_clean = question_clean.replace(phrase, " ")

    # Bỏ các từ đơn lẻ không mang nghĩa chủ đề
    remove_singles = [
        "lại", "lai", "về", "ve", "của", "cua", "trong",
        "với", "voi", "gì", "gi", "nào", "nao", "nữa", "nua",
        "thì", "thi", "mà", "ma", "để", "de", "hay",
        "vào", "vao", "ra", "lên", "len", "xuống", "xuong",
        "thêm", "them", "hơn", "hon", "rồi", "roi",
        "tôi", "toi", "bạn", "ban", "hỏi", "hoi",
    ]
    for w in remove_singles:
        question_clean = re.sub(rf'\b{re.escape(w)}\b', ' ', question_clean)

    question_clean = re.sub(r'\s+', ' ', question_clean).strip()
    return question_clean


def _normalize_text(text: str) -> str:
    """Chuẩn hóa text để so khớp theo tên nguồn."""
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_all_sources() -> list:
    """Lấy danh sách nguồn đang có trong ChromaDB (có cache)."""
    global _source_cache
    if _source_cache is not None:
        return _source_cache

    collection = get_collection()
    raw = collection.get(include=["metadatas"])
    metadatas = raw.get("metadatas", []) if raw else []

    seen = set()
    sources = []
    for meta in metadatas:
        src = meta.get("source") if isinstance(meta, dict) else None
        if src and src not in seen:
            seen.add(src)
            sources.append(src)

    _source_cache = sources
    return sources


def _find_matching_sources(question: str) -> list:
    """Match nguồn theo tên file PDF để ưu tiên đúng chủ đề."""
    q_norm = _normalize_text(question)
    if not q_norm:
        return []

    for alias_query, alias_target in SOURCE_QUERY_ALIASES.items():
        if alias_query in q_norm and alias_target not in q_norm:
            q_norm = f"{q_norm} {alias_target}"

    scored_matches = []
    for source in _get_all_sources():
        source_norm = _normalize_text(source.replace(".pdf", ""))
        if not source_norm:
            continue

        if q_norm in source_norm or source_norm in q_norm:
            score = 100 + len(source_norm)
            scored_matches.append((source, score))
            continue

        source_tokens = [t for t in source_norm.split() if len(t) >= 3]
        overlap = sum(1 for t in source_tokens if t in q_norm)
        if overlap >= 3:
            score = overlap * 10 + len(source_norm) * 0.1
            scored_matches.append((source, score))

    if not scored_matches:
        return []

    scored_matches.sort(key=lambda x: x[1], reverse=True)
    return [source for source, _ in scored_matches[:3]]


def _source_priority_search(question: str, limit_per_source: int = 8) -> list:
    """Ưu tiên nguồn match theo tên file, nhưng vẫn semantic-search trong chính nguồn đó."""
    matched_sources = _find_matching_sources(question)
    if not matched_sources:
        return []

    collection = get_collection()
    prioritized = []

    for source in matched_sources:
        try:
            q = collection.query(
                query_texts=[question],
                where={"source": {"$eq": source}},
                n_results=limit_per_source,
                include=["documents", "metadatas", "distances"],
            )

            docs = (q.get("documents") or [[]])[0]
            metas = (q.get("metadatas") or [[]])[0]
            dists = (q.get("distances") or [[]])[0]

            for doc, meta, dist in zip(docs, metas, dists):
                prioritized.append({
                    "content": doc,
                    "metadata": meta if isinstance(meta, dict) else {},
                    "score": float(dist),
                    "boosted_score": float(dist) - 0.08,  # boost nhẹ vì đúng source
                    "source_priority": True,
                })
        except Exception as e:
            print(f"[RAG] Source-priority search lỗi với {source}: {e}")

    if prioritized:
        print(f"[RAG] Source-priority match: {matched_sources}")
    return prioritized


# ======================== LLM CALLS ========================

def _messages_to_prompt(messages: list) -> str:
    """Chuyển danh sách messages (OpenAI format) thành prompt text cho Gemini."""
    return "\n\n".join(
        f"[{m.get('role', 'user').upper()}]\n{m.get('content', '')}"
        for m in messages
    )


def _call_groq(messages: list) -> str:
    """Gọi Groq API. Raise exception nếu lỗi (để fallback hoạt động)."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY trống!")

    print(f"[LLM] 🤖 Gọi Groq (model: {GROQ_MODEL}, messages: {len(messages)})...")
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
        top_p=0.9,
    )
    choice = response.choices[0]
    answer = (choice.message.content or "").strip()
    finish = getattr(choice, "finish_reason", "unknown")
    usage = getattr(response, "usage", None)
    print(f"[LLM] ✅ Groq OK ({len(answer)} ký tự, finish={finish}, usage={usage})")
    if finish == "length":
        print("[LLM] ⚠️ Groq bị cắt do max_tokens! Cần tăng max_tokens.")
    return answer


def _call_gemini(messages: list) -> str:
    """Gọi Gemini API với auto-fallback qua nhiều model."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY trống!")

    genai.configure(api_key=GEMINI_API_KEY)
    prompt = _messages_to_prompt(messages)

    # Xây dựng danh sách model: ưu tiên model cấu hình, sau đó fallback
    models_to_try = [GEMINI_MODEL]
    for m in GEMINI_FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model_name in models_to_try:
        try:
            print(f"[LLM] 🤖 Gọi Gemini (model: {model_name})...")

            # gemini-2.5-* là model "thinking" → max_output_tokens bao gồm
            # cả thinking tokens, cần đặt cao hơn để không bị cắt câu trả lời
            if "2.5" in model_name:
                gen_config = {
                    "temperature": 0.3,
                    "max_output_tokens": 8192,
                }
            else:
                gen_config = {
                    "temperature": 0.3,
                    "max_output_tokens": 2048,
                }

            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config=gen_config)
            answer = (getattr(response, "text", "") or "").strip()
            print(f"[LLM] ✅ Gemini OK - {model_name} ({len(answer)} ký tự)")
            return answer
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            # Nếu lỗi quota/rate-limit → thử model tiếp theo
            if "resource_exhausted" in err_str or "429" in err_str or "quota" in err_str:
                print(f"[LLM] ⚠️ Gemini {model_name} quota exceeded, thử model tiếp...")
                continue
            # Lỗi khác (auth, network...) → raise ngay
            raise

    # Tất cả model đều hết quota
    raise RuntimeError(f"Tất cả Gemini models đều hết quota: {last_error}")


def _call_llm_with_fallback(messages: list) -> str:
    """Gọi LLM: ưu tiên Groq → fallback Gemini → extractive fallback."""
    global _last_llm_error
    try:
        answer = _call_groq(messages)
        if answer:
            print("[LLM] provider=groq")
            _last_llm_error = ""
            return answer
    except Exception as e:
        _last_llm_error = str(e)
        print(f"[LLM] ❌ Groq failed: {e}")

    try:
        answer = _call_gemini(messages)
        if answer:
            print("[LLM] provider=gemini")
            _last_llm_error = ""
            return answer
    except Exception as e2:
        _last_llm_error = str(e2)
        print(f"[LLM] ❌ Gemini failed: {e2}")

    print("[LLM] provider=extractive_fallback")
    return ""


def _extractive_fallback_answer(question: str, context: str) -> str:
    """Fallback cục bộ khi LLM lỗi: trích xuất câu phù hợp nhất từ context."""
    if not context:
        return "Xin lỗi, tôi không tìm thấy thông tin phù hợp trong tài liệu."

    clean_lines = []
    for line in context.splitlines():
        line = line.strip()
        if not line or line.startswith("[Nguồn:") or line == "---":
            continue
        clean_lines.append(line)

    if not clean_lines:
        return "Xin lỗi, tôi không tìm thấy thông tin phù hợp trong tài liệu."

    q_norm = _normalize_text(question)
    q_tokens = [t for t in q_norm.split() if len(t) >= 3]

    def score_line(line: str) -> int:
        ln = _normalize_text(line)
        return sum(1 for t in q_tokens if t in ln)

    scored = sorted(clean_lines, key=score_line, reverse=True)
    best = [ln for ln in scored[:5] if score_line(ln) > 0]
    if not best:
        best = clean_lines[:3]

    merged = " ".join(best)

    # Câu hỏi về thời gian → trích năm
    if any(k in q_norm for k in ["nam nao", "vao nam", "thoi gian nao", "khi nao"]):
        year_match = re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", merged)
        if year_match:
            return f"Theo tài liệu, mốc thời gian liên quan là: {', '.join(dict.fromkeys(year_match))}."

    # Ghép các câu hay nhất, cắt tại dấu câu cuối để không bị cụt
    text = merged[:1200]
    cut = max(text.rfind("."), text.rfind("!"), text.rfind("?"), text.rfind(";"))
    if cut > 100:
        text = text[:cut + 1]

    return text


# ======================== EMBEDDING SEARCH ========================

def _embedding_search(question: str, top_k: int = MAX_TOTAL_CHUNKS) -> list:
    """
    Tìm kiếm bằng embedding từ ChromaDB.
    Chiến lược: Nếu match được nguồn theo tên file → ưu tiên tuyệt đối nguồn đó.
    Chỉ bổ sung general results cho các slot còn lại (đa dạng nguồn).
    """
    try:
        priority_results = _source_priority_search(question, limit_per_source=8)
        general_results = search(question, top_k=top_k * 2, max_distance=0.8)

        if not general_results and not priority_results:
            print("[RAG] Không tìm thấy kết quả embedding search.")
            return []

        # ===== TRƯỜNG HỢP 1: Có source-priority match =====
        if priority_results:
            # Sắp xếp priority results theo distance thực (tốt nhất trước)
            priority_results.sort(key=lambda x: x["score"])

            # Phân bổ: priority chiếm phần lớn, general bổ sung
            priority_slots = min(len(priority_results), top_k - 4)
            final = priority_results[:priority_slots]

            # Dedup set
            seen = set()
            for r in final:
                key = (
                    r.get("metadata", {}).get("source", ""),
                    r.get("metadata", {}).get("chunk_index", -1),
                    r.get("content", "")[:80],
                )
                seen.add(key)

            # Bổ sung general results cho đa dạng (ưu tiên nguồn khác)
            priority_sources = {r.get("metadata", {}).get("source", "") for r in final}

            for r in (general_results or []):
                if len(final) >= top_k:
                    break
                key = (
                    r.get("metadata", {}).get("source", ""),
                    r.get("metadata", {}).get("chunk_index", -1),
                    r.get("content", "")[:80],
                )
                if key in seen:
                    continue
                seen.add(key)
                final.append({
                    "content": r["content"],
                    "metadata": r["metadata"],
                    "score": r["score"],
                    "boosted_score": r["score"],
                })

            print(f"[RAG] Embedding search: {len(final)} kết quả (priority={priority_slots})")
            for i, r in enumerate(final[:5]):
                src = r.get("metadata", {}).get("source", "?")
                prio = "★" if r.get("source_priority") else " "
                print(f"  [{i+1}]{prio} dist={r['score']:.4f} | {src}")

            return final

        # ===== TRƯỜNG HỢP 2: Không có source match → keyword boosting =====
        keywords = _extract_keywords(question)
        boosted_results = []
        for r in (general_results or []):
            content_lower = r["content"].lower()
            source_lower = r.get("metadata", {}).get("source", "").lower()
            boost = 0.0

            for kw in keywords:
                kw_lower = kw.lower()
                # Chỉ boost cho keyword đủ dài (≥ 4 chars) để tránh false positive
                if len(kw_lower) < 4:
                    continue
                if kw_lower in content_lower:
                    boost -= 0.02
                if kw_lower in source_lower:
                    boost -= 0.05

            boost = max(-0.25, boost)
            boosted_results.append({
                "content": r["content"],
                "metadata": r["metadata"],
                "score": r["score"],
                "boosted_score": r["score"] + boost,
            })

        boosted_results.sort(key=lambda x: x["boosted_score"])
        boosted_results = boosted_results[:top_k]

        print(f"[RAG] Embedding search: {len(boosted_results)} kết quả (general)")
        for i, r in enumerate(boosted_results[:5]):
            src = r.get("metadata", {}).get("source", "?")
            print(f"  [{i+1}] dist={r['score']:.4f} boosted={r.get('boosted_score', r['score']):.4f} | {src}")

        return boosted_results

    except Exception as e:
        print(f"[RAG] Lỗi embedding search: {e}")
        return []


def _extract_keywords(question: str) -> list:
    """Trích xuất từ khóa quan trọng từ câu hỏi."""
    stop_words = {
        "là", "gì", "của", "và", "có", "được", "trong", "cho", "với",
        "này", "đó", "các", "một", "những", "về", "từ", "đến", "như",
        "thế", "nào", "bao", "nhiêu", "khi", "nào", "ở", "đâu", "ai",
        "tại", "sao", "vì", "thì", "mà", "để", "hay", "hoặc", "nhưng",
        "nếu", "vậy", "rồi", "lại", "cũng", "đã", "sẽ", "đang", "rất",
        "hãy", "nêu", "cho", "biết", "trình", "bày", "tóm", "tắt",
        "diễn", "biến", "phân", "tích", "giải", "thích", "mô", "tả",
        "năm", "ngày", "tháng", "vào", "ra", "lên", "xuống", "trên",
        "dưới", "không", "chỉ", "cần", "tôi", "bạn", "hỏi",
    }

    words = re.findall(r'\w+', question.lower())
    keywords = [w for w in words if w not in stop_words and len(w) >= 3]

    bigrams = []
    for i in range(len(words) - 1):
        bigram = words[i] + " " + words[i + 1]
        if words[i] not in stop_words and words[i + 1] not in stop_words:
            bigrams.append(bigram)

    return keywords + bigrams


def _build_context(chunks: list, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Xây dựng context từ chunks, nhóm theo nguồn và sắp xếp theo thứ tự tài liệu."""
    if not chunks:
        return ""

    # Nhóm chunks theo source
    source_groups = {}
    for chunk in chunks:
        source = chunk.get("metadata", {}).get("source", "?")
        if source not in source_groups:
            source_groups[source] = []
        source_groups[source].append(chunk)

    # Sắp xếp mỗi nhóm theo chunk_index (thứ tự tài liệu)
    for source in source_groups:
        source_groups[source].sort(
            key=lambda x: x.get("metadata", {}).get("chunk_index", 0)
        )

    # Xây dựng context theo thứ tự: nguồn có nhiều chunks nhất trước
    sorted_sources = sorted(source_groups.items(), key=lambda x: -len(x[1]))

    context_parts = []
    total_chars = 0

    for source, group_chunks in sorted_sources:
        source_header = f"[Nguồn: {source}]"
        source_text = source_header

        for chunk in group_chunks:
            content = chunk.get("content", "").strip()
            addition = f"\n{content}"

            if total_chars + len(source_text) + len(addition) > max_chars:
                remaining = max_chars - total_chars - len(source_text)
                if remaining > 100:
                    source_text += addition[:remaining] + "..."
                break
            source_text += addition

        if len(source_text) > len(source_header) + 5:
            context_parts.append(source_text)
            total_chars += len(source_text)

        if total_chars >= max_chars:
            break

    return "\n\n---\n\n".join(context_parts)


# ======================== PUBLIC API ========================

def retrieve_context(query: str, top_k: int = 10) -> str:
    """Tìm kiếm context liên quan từ ChromaDB."""
    results = _embedding_search(query, top_k=top_k)
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

# ======================== DETECT NO-INFO ANSWER ========================

def _detect_no_info_answer(answer: str) -> bool:
    """
    Phát hiện khi LLM trả lời dạng 'tài liệu không có thông tin'.
    Chỉ detect khi câu trả lời CHÍNH LÀ lời từ chối, không phải nhắc đến trong ngữ cảnh khác.
    """
    if not answer:
        return True

    answer_lower = answer.lower().strip()

    # Câu trả lời quá ngắn (< 60 ký tự) VÀ chứa pattern từ chối
    is_short = len(answer.strip()) < 80

    # Pattern chỉ match khi đứng ĐẦU câu hoặc chiếm phần lớn câu trả lời
    strong_no_info = [
        "tài liệu tham khảo không cung cấp",
        "tài liệu không cung cấp",
        "tài liệu không có thông tin",
        "tài liệu không đề cập",
        "không tìm thấy thông tin",
        "không có thông tin trong tài liệu",
        "không thể trả lời dựa trên tài liệu",
        "ngoài phạm vi tài liệu",
        "thông tin này không có trong",
        "tài liệu không chứa",
        "không có đủ thông tin để trả lời",
    ]

    for pattern in strong_no_info:
        if pattern in answer_lower:
            # Nếu câu dài (>300 chars) và pattern chỉ xuất hiện 1 lần ở giữa → có thể OK
            if len(answer.strip()) > 300:
                # Kiểm tra pattern có ở 100 ký tự đầu không
                if pattern in answer_lower[:150]:
                    print(f"[RAG] Phát hiện 'no-info' (đầu câu): '{pattern}'")
                    return True
                # Pattern ở giữa/cuối câu dài → bỏ qua
                continue
            print(f"[RAG] Phát hiện 'no-info': '{pattern}'")
            return True

    # Câu quá ngắn + chứa từ khóa từ chối nhẹ
    if is_short:
        weak_patterns = ["không có thông tin", "không cung cấp", "không đề cập"]
        for p in weak_patterns:
            if p in answer_lower:
                print(f"[RAG] Phát hiện 'no-info' (ngắn): '{p}'")
                return True

    return False


# ======================== WIKI ENHANCED ANSWER ========================

def _ask_with_wiki_context(question: str, wiki_result: dict) -> str:
    """
    Gọi LLM với context từ Wikipedia crawl.
    """
    if not wiki_result.get("success") or not wiki_result.get("context"):
        return ""

    context = wiki_result["context"]
    sources = wiki_result.get("sources", [])

    source_text = ""
    if sources:
        source_list = "\n".join(f"  - {s}" for s in sources[:3])
        source_text = f"\n\nNguồn: {source_list}"

    system_msg = (
        "Bạn là trợ lý AI chuyên về lịch sử Việt Nam. "
        "Dưới đây là thông tin từ Wikipedia tiếng Việt. "
        "Hãy trả lời câu hỏi dựa trên thông tin này. "
        "Trả lời bằng tiếng Việt, đầy đủ, chi tiết, có cấu trúc rõ ràng. "
        "Cuối câu trả lời, ghi rõ nguồn: '(Nguồn: Wikipedia)'"
    )

    user_msg = f"TÀI LIỆU TỪ WIKIPEDIA:\n{context}\n\nCÂU HỎI: {question}{source_text}"

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    try:
        answer = _call_llm_with_fallback(messages)
        if answer:
            if "(Nguồn: Wikipedia)" not in answer and "(nguồn:" not in answer.lower():
                answer += "\n\n*(Nguồn: Wikipedia)*"
            return answer
    except Exception as e:
        print(f"[RAG] ❌ LLM with wiki context failed: {e}")

    return ""

def ask_pg(question: str, session_id: str = "default") -> dict:
    """Trả lời câu hỏi lịch sử bằng RAG (ChromaDB + Groq/Gemini)."""
    try:
        question = (question or "").strip()
        if not question:
            return {
                "answer": "Vui lòng nhập câu hỏi.",
                "sources": [],
                "evaluation": {"sufficient": False, "confidence": "Thấp"},
            }

        if session_id not in _chat_histories:
            _chat_histories[session_id] = []

        is_follow_up = (
            _is_follow_up_question(question)
            and session_id in _session_topics
            and bool(_session_topics.get(session_id))
        )

        # ===================== XÂY DỰNG SEARCH QUERY =====================
        # Follow-up: kết hợp topic trước đó + câu hỏi mới để search chính xác
        if is_follow_up:
            previous_topic = _session_topics.get(session_id, "")
            search_query = f"{previous_topic} {question}"
            print(f"[RAG] Follow-up detected → combined query: {search_query[:80]}")
        else:
            search_query = question

        # ===================== LUÔN TÌM KIẾM MỚI =====================
        results = _embedding_search(search_query, top_k=MAX_TOTAL_CHUNKS)

        if not results:
            return {
                "answer": "Xin lỗi, tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu.",
                "sources": [],
                "evaluation": {"sufficient": False, "confidence": "Thấp"},
            }

        context = _build_context(results, max_chars=MAX_CONTEXT_CHARS)

        sources = []
        seen_sources = set()
        for r in results:
            src = r.get("metadata", {}).get("source", "unknown")
            if src not in seen_sources:
                seen_sources.add(src)
                sources.append(src)

        distances = [r.get("score", 1.0) for r in results if isinstance(r.get("score", None), (int, float))]
        avg_distance = sum(distances) / len(distances) if distances else 1.0

        sufficient = avg_distance <= 0.80
        if avg_distance <= 0.35:
            confidence = "Cao"
        elif avg_distance <= 0.60:
            confidence = "Trung bình"
        else:
            confidence = "Thấp"

        evaluation = {"sufficient": sufficient, "confidence": confidence}

        # Lưu topic cho follow-up sau
        if not is_follow_up:
            _session_topics[session_id] = _extract_topic(question)
        _session_contexts[session_id] = context
        _session_contexts[f"{session_id}_sources"] = sources

        # Debug: in 200 chars đầu context
        print(f"[RAG] Context ({len(context)} chars): {context[:200]}...")

        # ===================== TẠO MESSAGES =====================
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        history = _chat_histories.get(session_id, [])
        for m in history[-(MAX_HISTORY_TURNS * 2):]:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": m["content"]})

        context_note = ""
        if is_follow_up:
            context_note = (
                "\n\n⚠️ QUAN TRỌNG: Người dùng đang hỏi tiếp về chủ đề trước. "
                "Hãy kết hợp ngữ cảnh hội thoại trước đó để hiểu câu hỏi."
            )

        user_message = f"""TÀI LIỆU THAM KHẢO (CHỈ dựa trên nội dung bên dưới để trả lời):
{context}{context_note}

CÂU HỎI:
{question}

YÊU CẦU:
- Trả lời đúng trọng tâm câu hỏi dựa trên TÀI LIỆU THAM KHẢO ở trên.
- Nếu câu hỏi chỉ hỏi một thông tin cụ thể (năm, ngày, tên, địa điểm...), trả lời ngắn gọn, trực tiếp.
- Chỉ trình bày dài khi người dùng yêu cầu chi tiết/phân tích/diễn biến.
- Không bịa đặt thông tin ngoài tài liệu.
"""

        messages.append({"role": "user", "content": user_message})

        # Giảm kích thước nếu quá dài
        total_chars = sum(len(m["content"]) for m in messages)
        estimated_tokens = total_chars // 3
        if estimated_tokens > 10000:
            print(f"[RAG] ⚠️ Token cao ({estimated_tokens}), rút gọn context...")
            short_context = context[: MAX_CONTEXT_CHARS // 2]
            last_cut = max(short_context.rfind("."), short_context.rfind("\n"))
            if last_cut > 0:
                short_context = short_context[: last_cut + 1]
            short_context += "\n\n[... tài liệu được rút gọn ...]"

            messages[-1] = {
                "role": "user",
                "content": f"""TÀI LIỆU THAM KHẢO:
{short_context}

CÂU HỎI:
{question}

Trả lời đúng trọng tâm dựa trên tài liệu. Ngắn gọn nếu hỏi cụ thể. Chỉ chi tiết khi được yêu cầu.
""",
            }

        # ===================== GỌI LLM =====================
        answer = _call_llm_with_fallback(messages)

        # Fallback extractive nếu cả Groq + Gemini đều lỗi
        if not answer or not answer.strip():
            fallback = _extractive_fallback_answer(question, context)
            if "rate_limit" in _last_llm_error.lower() or "429" in _last_llm_error.lower():
                answer = (
                    "⚠️ Hệ thống AI tạm thời chạm giới hạn quota. "
                    "Dưới đây là câu trả lời trích xuất trực tiếp từ tài liệu:\n\n"
                    f"{fallback}"
                )
            else:
                answer = fallback

# ===================== AUTO WIKI CRAWL =====================
        # Nếu câu trả lời dạng "không có thông tin" → crawl Wikipedia
        if _detect_no_info_answer(answer) and callable(wiki_search_and_save):
            print("[RAG] 🌐 PDF không đủ thông tin → thử crawl Wikipedia...")

            wiki_result = wiki_search_and_save(question, max_pages=2)

            if wiki_result.get("success"):
                wiki_answer = _ask_with_wiki_context(question, wiki_result)

                if wiki_answer and not _detect_no_info_answer(wiki_answer):
                    print(f"[RAG] ✅ Wiki answer OK ({len(wiki_answer)} ký tự)")
                    if wiki_result.get("chunks_saved", 0) > 0:
                        print(f"[RAG] 💾 Đã lưu {wiki_result['chunks_saved']} chunks vào DB")
                    answer = wiki_answer
                else:
                    print("[RAG] ❌ Wiki answer vẫn không đủ thông tin")
            else:
                print("[RAG] ❌ Wikipedia crawl thất bại")

        # Lưu chat history
        _chat_histories[session_id].append({"role": "user", "content": question})
        _chat_histories[session_id].append({"role": "assistant", "content": answer})

        if len(_chat_histories[session_id]) > 30:
            _chat_histories[session_id] = _chat_histories[session_id][-30:]

        return {
            "answer": answer,
            "sources": sources,
            "evaluation": evaluation,
        }

    except Exception as e:
        print(f"[RAG] ask_pg error: {e}")
        return {
            "answer": "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi.",
            "sources": [],
            "evaluation": {"sufficient": False, "confidence": "Thấp"},
            "error": str(e),
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


def process_uploaded_pdf(uploaded_file) -> dict:
    """
    Xử lý file PDF được người dùng upload:
    1. Lưu tạm file
    2. Đọc nội dung PDF
    3. Chunk văn bản
    4. Index vào ChromaDB
    Returns: {"success": bool, "filename": str, "text": str, "chunks_count": int}
    """
    try:
        filename = uploaded_file.name
        print(f"[PDF] 📄 Processing uploaded file: {filename}")

        # Lưu file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        # Đọc nội dung PDF
        text = load_pdf_file(tmp_path)

        if not text or not text.strip():
            os.unlink(tmp_path)
            return {
                "success": False,
                "filename": filename,
                "text": "",
                "chunks_count": 0,
                "error": "Không thể trích xuất text từ PDF.",
            }

        # Chunk văn bản
        documents = [{"content": text, "source": filename}]
        chunks = chunk_documents(documents, chunk_size=800, chunk_overlap=200)

        if chunks:
            # Index vào ChromaDB
            create_vector_database(chunks)
            print(f"[PDF] ✅ Indexed {len(chunks)} chunks from {filename}")

        # Xóa file tạm
        os.unlink(tmp_path)

        return {
            "success": True,
            "filename": filename,
            "text": text,
            "chunks_count": len(chunks),
        }

    except Exception as e:
        print(f"[PDF] ❌ Error processing PDF: {e}")
        return {
            "success": False,
            "filename": getattr(uploaded_file, 'name', 'unknown'),
            "text": "",
            "chunks_count": 0,
            "error": str(e),
        }


def summarize_pdf_text(text: str, filename: str, session_id: str = "default") -> dict:
    """
    Tóm tắt nội dung PDF đã upload.
    """
    if not text or not text.strip():
        return {
            "answer": "Không có nội dung để tóm tắt.",
            "sources": [filename],
            "evaluation": {"sufficient": False, "confidence": "Thấp"},
        }

    # Giới hạn text để tránh vượt token limit
    max_chars = 10000
    truncated = text[:max_chars]
    if len(text) > max_chars:
        last_cut = max(truncated.rfind("."), truncated.rfind("\n"))
        if last_cut > 0:
            truncated = truncated[:last_cut + 1]
        truncated += "\n\n[... nội dung được rút gọn ...]"

    system_msg = (
        "Bạn là trợ lý AI chuyên tóm tắt tài liệu. "
        "Hãy tóm tắt nội dung tài liệu sau một cách chi tiết, có cấu trúc rõ ràng. "
        "Sử dụng tiếng Việt. Trình bày theo các mục chính với bullet points."
    )

    user_msg = f"""TÀI LIỆU CẦN TÓM TẮT (nguồn: {filename}):
{truncated}

Hãy tóm tắt nội dung chính của tài liệu trên. Trình bày rõ ràng, có cấu trúc."""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    try:
        answer = _call_llm_with_fallback(messages)
        if not answer:
            answer = "Không thể tóm tắt tài liệu lúc này. Vui lòng thử lại."

        return {
            "answer": answer,
            "sources": [filename],
            "evaluation": {"sufficient": True, "confidence": "Cao"},
        }
    except Exception as e:
        print(f"[PDF] ❌ Summarize error: {e}")
        return {
            "answer": f"Lỗi khi tóm tắt: {e}",
            "sources": [filename],
            "evaluation": {"sufficient": False, "confidence": "Thấp"},
        }