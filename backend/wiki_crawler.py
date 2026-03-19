"""
Wikipedia Crawler: Tìm kiếm và crawl nội dung từ Wikipedia tiếng Việt.
Sau khi crawl, tự động lưu vào ChromaDB để lần sau không cần crawl lại.
"""

import os
import re
import sys
import hashlib
import requests
from bs4 import BeautifulSoup

# Thêm path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from data_processing.indexing import get_collection


# ======================== CONFIG ========================

WIKI_API = "https://vi.wikipedia.org/w/api.php"
WIKI_BASE = "https://vi.wikipedia.org/wiki/"

HEADERS = {
    "User-Agent": "ChatbotLichSu/1.0 (Vietnamese History Chatbot; educational project)",
    "Accept-Language": "vi-VN,vi;q=0.9",
}

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


# ======================== EXTRACT KEYWORDS ========================

def _extract_search_keywords(question: str) -> str:
    """
    Trích xuất keywords chính từ câu hỏi để search Wiki chính xác hơn.
    Loại bỏ stopwords, giữ lại danh từ riêng và từ khóa lịch sử.
    """
    q = question.strip()

    # Loại bỏ dấu hỏi, câu mệnh lệnh
    q = re.sub(r"[?!.,;:\"'(){}[\]]", " ", q)

    # Stopwords tiếng Việt (mở rộng)
    stopwords = {
        "là", "gì", "nào", "khi", "như", "thế", "bao", "nhiêu",
        "ai", "đâu", "sao", "tại", "vì", "và", "của", "có", "được", "không",
        "trong", "với", "cho", "từ", "đến", "này", "đó", "các", "những",
        "một", "hai", "ba", "về", "theo", "trên", "dưới", "sau", "trước",
        "ra", "vào", "lên", "xuống", "đi", "lại", "rồi", "mà", "thì",
        "hãy", "kể", "tóm", "tắt", "trình", "bày", "giải", "thích",
        "diễn", "biến", "chi", "tiết", "cho", "biết", "liệt",
        "nêu", "mô", "tả", "viết", "nói", "nhắc", "đề", "cập",
        "sự", "kiện", "vào", "thời", "gian", "năm", "ngày", "tháng",
        "trả", "lời", "kèm", "nguồn", "câu", "hỏi", "xin",
        "ở", "bị", "đang", "sẽ", "đã", "cũng", "vẫn", "còn",
        "nên", "phải", "cần", "nếu", "hoặc", "hay",
        "rất", "quá", "lắm", "nhất", "hơn", "kém",
        "ta", "mình", "tôi", "bạn", "họ", "chúng",
        "thắng", "đánh", "lần", "diễn", "ra",
    }

    words = q.split()
    keywords = []

    i = 0
    while i < len(words):
        word = words[i].strip()

        # Giữ nguyên cụm từ viết hoa (danh từ riêng)
        if word and word[0].isupper() and i > 0:
            proper_noun = [word]
            j = i + 1
            while j < len(words) and words[j] and words[j][0].isupper():
                proper_noun.append(words[j])
                j += 1
            if len(proper_noun) >= 2:
                keywords.append(" ".join(proper_noun))
                i = j
                continue

        # Giữ số (năm, số liệu)
        if re.match(r"\d+", word):
            keywords.append(word)
            i += 1
            continue

        # Lọc stopwords
        if word.lower() not in stopwords and len(word) >= 2:
            keywords.append(word)

        i += 1

    result = " ".join(keywords)

    # Nếu keywords quá ít, dùng câu gốc rút gọn
    if len(keywords) < 2:
        # Lấy 6 từ dài nhất
        words_sorted = sorted(q.split(), key=len, reverse=True)
        meaningful = [w for w in words_sorted if w.lower() not in stopwords and len(w) >= 2]
        result = " ".join(meaningful[:6])

    print(f"[WIKI] Keywords extracted: '{question[:60]}' → '{result}'")
    return result


# ======================== SEARCH WIKIPEDIA ========================

def _search_wiki(query: str, limit: int = 5) -> list:
    """
    Tìm kiếm bài viết trên Wikipedia tiếng Việt.
    Thử nhiều query variants để tăng cơ hội tìm đúng.
    """
    # Extract keywords từ câu hỏi gốc
    keywords = _extract_search_keywords(query)

    # Tạo các variants search
    search_queries = []
    if keywords and keywords != query:
        search_queries.append(keywords)

    # Thêm query gốc rút gọn (max 60 ký tự)
    short_query = query[:60].strip()
    if short_query not in search_queries:
        search_queries.append(short_query)

    # Thêm "lịch sử" vào keyword
    if "lịch sử" not in keywords.lower():
        search_queries.append(f"{keywords} lịch sử")

    all_results = []
    seen_titles = set()

    for sq in search_queries:
        if len(all_results) >= limit:
            break

        params = {
            "action": "query",
            "list": "search",
            "srsearch": sq,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }
        try:
            r = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json()

            for item in data.get("query", {}).get("search", []):
                title = item["title"]
                if title not in seen_titles:
                    seen_titles.add(title)
                    all_results.append({
                        "title": title,
                        "pageid": item["pageid"],
                        "snippet": re.sub(r"<[^>]+>", "", item.get("snippet", "")),
                    })

            print(f"[WIKI] 🔍 Search '{sq}' → {len(data.get('query', {}).get('search', []))} kết quả")

        except Exception as e:
            print(f"[WIKI] ❌ Search error for '{sq}': {e}")

    # Sắp xếp: ưu tiên bài có title/snippet chứa keywords
    kw_lower = keywords.lower().split()

    def relevance_score(item):
        score = 0
        title_lower = item["title"].lower()
        snippet_lower = item.get("snippet", "").lower()
        for kw in kw_lower:
            if kw in title_lower:
                score += 3
            if kw in snippet_lower:
                score += 1
        return -score  # sort ascending → cao nhất lên đầu

    all_results.sort(key=relevance_score)

    print(f"[WIKI] Tổng: {len(all_results)} bài, top: {[r['title'] for r in all_results[:3]]}")
    return all_results[:limit]


# ======================== CRAWL PAGE CONTENT ========================

def _get_wiki_content(title: str, max_chars: int = 15000) -> str:
    """
    Lấy nội dung text của bài Wikipedia theo title.
    """
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "utf8": 1,
        "disabletoc": 1,
    }
    try:
        r = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()

        html = data.get("parse", {}).get("text", {}).get("*", "")
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        # Xoá các phần không cần
        for tag in soup(["script", "style", "sup", "img"]):
            tag.decompose()

        for selector in ["div.navbox", "div.metadata", "div.reflist",
                         "div.thumb", "div.toc", "div.hatnote",
                         "div.mw-references-wrap", "span.mw-editsection",
                         "table.infobox", "table.wikitable"]:
            for el in soup.select(selector):
                el.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # Làm sạch
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\[\d+\]", "", text)
        text = re.sub(r"\[cần dẫn nguồn\]", "", text)
        text = re.sub(r"\[sửa \| sửa mã nguồn\]", "", text)

        # Lọc dòng quá ngắn
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 10]
        result = "\n".join(lines)

        # Giới hạn
        if len(result) > max_chars:
            result = result[:max_chars]

        print(f"[WIKI] ✅ Crawled '{title}': {len(result)} ký tự")
        return result

    except Exception as e:
        print(f"[WIKI] ❌ Crawl error '{title}': {e}")
        return ""


# ======================== CHUNK TEXT ========================

def _chunk_text(text: str, source: str) -> list:
    """Chia text thành các chunk nhỏ để lưu vào ChromaDB."""
    if not text:
        return []

    chunks = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + CHUNK_SIZE

        if end < len(text):
            for sep in [".\n", ". ", "\n\n", "\n"]:
                pos = text.rfind(sep, start + CHUNK_SIZE // 2, end + 100)
                if pos > start:
                    end = pos + len(sep)
                    break

        chunk_text = text[start:end].strip()
        if len(chunk_text) > 30:
            chunks.append({
                "text": chunk_text,
                "source": source,
                "chunk_index": idx,
            })
            idx += 1

        start = end - CHUNK_OVERLAP
        if start >= len(text):
            break

    return chunks


# ======================== SAVE TO CHROMADB ========================

def _save_to_chromadb(chunks: list, source_name: str) -> int:
    """Lưu chunks vào ChromaDB. Skip nếu đã tồn tại."""
    if not chunks:
        return 0

    try:
        collection = get_collection()

        existing = collection.get(
            where={"source": source_name},
            limit=1,
        )
        if existing and existing.get("ids") and len(existing["ids"]) > 0:
            print(f"[WIKI] ℹ️ Source '{source_name}' đã có trong DB, skip")
            return 0

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            chunk_hash = hashlib.md5(
                f"{source_name}_{chunk['chunk_index']}_{chunk['text'][:50]}".encode()
            ).hexdigest()[:12]
            doc_id = f"wiki_{chunk_hash}"

            ids.append(doc_id)
            documents.append(chunk["text"])
            metadatas.append({
                "source": source_name,
                "chunk_index": chunk["chunk_index"],
                "origin": "wikipedia",
            })

        batch_size = 50
        saved = 0
        for i in range(0, len(ids), batch_size):
            collection.add(
                ids=ids[i:i + batch_size],
                documents=documents[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size],
            )
            saved += len(ids[i:i + batch_size])

        print(f"[WIKI] 💾 Đã lưu {saved} chunks từ '{source_name}' vào ChromaDB")
        return saved

    except Exception as e:
        print(f"[WIKI] ❌ Lỗi lưu ChromaDB: {e}")
        return 0


# ======================== MAIN FUNCTION ========================

def wiki_search_and_save(query: str, max_pages: int = 2) -> dict:
    """
    Tìm kiếm Wikipedia → Crawl → Lưu vào ChromaDB.
    """
    result = {
        "success": False,
        "context": "",
        "sources": [],
        "chunks_saved": 0,
    }

    query = (query or "").strip()
    if not query:
        return result

    # Bước 1: Tìm kiếm
    search_results = _search_wiki(query, limit=max_pages + 2)
    if not search_results:
        return result

    # Bước 2: Crawl
    all_content = []
    total_saved = 0

    for sr in search_results[:max_pages]:
        title = sr["title"]
        content = _get_wiki_content(title, max_chars=15000)

        if not content or len(content) < 100:
            continue

        context_part = content[:4000]
        all_content.append(context_part)
        result["sources"].append(f"Wikipedia: {title}")

        # Bước 3: Lưu vào DB
        source_name = f"Wikipedia - {title}.wiki"
        chunks = _chunk_text(content, source_name)
        saved = _save_to_chromadb(chunks, source_name)
        total_saved += saved

    if all_content:
        result["context"] = "\n\n---\n\n".join(all_content)
        result["success"] = True
        result["chunks_saved"] = total_saved
        print(f"[WIKI] ✅ Tổng: {len(all_content)} bài, {total_saved} chunks mới")

    return result


if __name__ == "__main__":
    r = wiki_search_and_save("kháng chiến chống quân Mông Nguyên")
    print(f"\nSuccess: {r['success']}")
    print(f"Sources: {r['sources']}")
    print(f"Chunks saved: {r['chunks_saved']}")
    if r["context"]:
        print(f"Preview: {r['context'][:500]}...")