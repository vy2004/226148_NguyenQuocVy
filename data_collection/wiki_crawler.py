import wikipedia
import re

wikipedia.set_lang("vi")

def search_wikipedia(query: str, max_results: int = 3) -> list[dict]:
    """
    Tìm kiếm Wikipedia tiếng Việt theo query.
    Trả về danh sách dict gồm title, content, url.
    """
    results = []
    try:
        search_results = wikipedia.search(query, results=max_results)
        for title in search_results:
            try:
                page = wikipedia.page(title, auto_suggest=False)
                content = clean_text(page.content)
                results.append({
                    "title": page.title,
                    "content": content,
                    "url": page.url,
                    "source": "wikipedia"
                })
            except (wikipedia.DisambiguationError, wikipedia.PageError):
                continue
    except Exception as e:
        print(f"Lỗi tìm kiếm Wikipedia: {e}")
    return results

def clean_text(text: str) -> str:
    """Loại bỏ phần thừa trong nội dung Wikipedia."""
    # Bỏ các section không cần thiết
    remove_sections = ["Tham khảo", "Liên kết ngoài", "Chú thích", "Xem thêm"]
    for section in remove_sections:
        pattern = rf"==\s*{section}\s*==.*"
        text = re.split(pattern, text)[0]
    # Bỏ ký hiệu wiki thừa
    text = re.sub(r"={2,}", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()