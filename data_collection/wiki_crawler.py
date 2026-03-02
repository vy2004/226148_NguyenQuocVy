"""
Module crawl dữ liệu từ Wikipedia tiếng Việt.
"""

import wikipedia
import os
import re
import time


# Đặt ngôn ngữ tiếng Việt
wikipedia.set_lang("vi")


def search_wikipedia(query: str, max_results: int = 3) -> list:
    """
    Tìm kiếm và lấy nội dung bài viết từ Wikipedia tiếng Việt.
    
    Args:
        query: từ khóa tìm kiếm
        max_results: số bài tối đa
    
    Returns:
        Danh sách dict {"title": "...", "content": "...", "url": "..."}
    """
    results = []

    try:
        # Tìm kiếm các bài viết liên quan
        search_results = wikipedia.search(query, results=max_results)
        print(f"🔍 Tìm thấy {len(search_results)} kết quả cho '{query}'")

        for title in search_results:
            try:
                page = wikipedia.page(title, auto_suggest=False)
                content = page.content

                # Loại bỏ phần tham khảo, liên kết ngoài
                content = re.split(r'\n==\s*(Tham khảo|Chú thích|Liên kết ngoài|Xem thêm)\s*==', content)[0]
                content = content.strip()

                if len(content) < 100:
                    print(f"  ⚠️ Bỏ qua '{title}' (nội dung quá ngắn)")
                    continue

                results.append({
                    "title": page.title,
                    "content": content,
                    "url": page.url
                })
                print(f"  ✅ Đã lấy: {page.title} ({len(content)} ký tự)")

                time.sleep(0.5)  # Tránh spam Wikipedia

            except wikipedia.exceptions.DisambiguationError as e:
                print(f"  ⚠️ '{title}' có nhiều nghĩa, thử lấy kết quả đầu tiên...")
                try:
                    if e.options:
                        page = wikipedia.page(e.options[0], auto_suggest=False)
                        content = page.content
                        content = re.split(r'\n==\s*(Tham khảo|Chú thích|Liên kết ngoài|Xem thêm)\s*==', content)[0]
                        if len(content) >= 100:
                            results.append({
                                "title": page.title,
                                "content": content.strip(),
                                "url": page.url
                            })
                            print(f"  ✅ Đã lấy: {page.title}")
                except Exception:
                    print(f"  ❌ Không thể lấy '{title}'")

            except wikipedia.exceptions.PageError:
                print(f"  ❌ Không tìm thấy trang '{title}'")

            except Exception as e:
                print(f"  ❌ Lỗi khi lấy '{title}': {e}")

    except Exception as e:
        print(f"❌ Lỗi tìm kiếm Wikipedia: {e}")

    return results


def save_wiki_to_raw(articles: list, raw_dir: str = None) -> list:
    """
    Lưu bài viết Wikipedia vào thư mục data/raw/ dưới dạng .txt
    
    Returns:
        Danh sách file đã lưu
    """
    if raw_dir is None:
        raw_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "raw"
        )
    
    os.makedirs(raw_dir, exist_ok=True)
    saved_files = []

    for article in articles:
        title = article["title"]
        # Tạo tên file an toàn
        safe_name = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        filename = f"wiki_{safe_name}.txt"
        filepath = os.path.join(raw_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n")
            f.write(f"# Nguồn: {article.get('url', 'Wikipedia')}\n\n")
            f.write(article["content"])

        saved_files.append(filepath)
        print(f"  💾 Đã lưu: {filename}")

    return saved_files