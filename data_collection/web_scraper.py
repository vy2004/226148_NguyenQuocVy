"""
Scrape nội dung từ các trang lịch sử uy tín.
"""
import requests
from bs4 import BeautifulSoup

HISTORY_SITES = {
    "lichsuvietnam.vn": {
        "content_selector": "div.entry-content",
        "title_selector": "h1.entry-title"
    },
    "nghiencuulichsu.com": {
        "content_selector": "div.td-post-content",
        "title_selector": "h1.entry-title"
    },
}

def scrape_history_site(url: str) -> dict | None:
    """Scrape trang lịch sử theo cấu hình riêng từng site."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Xác định domain
        domain = None
        for site in HISTORY_SITES:
            if site in url:
                domain = site
                break
        
        if domain:
            config = HISTORY_SITES[domain]
            title_tag = soup.select_one(config["title_selector"])
            content_tag = soup.select_one(config["content_selector"])
            
            title = title_tag.get_text().strip() if title_tag else ""
            content = content_tag.get_text().strip() if content_tag else ""
        else:
            # Fallback: lấy tất cả thẻ <p>
            title = soup.title.string if soup.title else ""
            paragraphs = soup.find_all("p")
            content = "\n".join(
                p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50
            )
        
        if len(content) < 200:
            return None
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "source": domain or "web"
        }
    except Exception as e:
        print(f"Lỗi scrape {url}: {e}")
        return None