"""
Tìm kiếm Google và scrape trang web.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# Danh sách domain uy tín về lịch sử
TRUSTED_DOMAINS = [
    "vi.wikipedia.org",
    "lichsuvietnam.vn",
    "nghiencuulichsu.com",
    "baotanglichsu.vn",
    "vansudia.net",
]


def google_search(query, num_results=5):
    """Tìm kiếm Google, trả về danh sách URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}&hl=vi"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("/url?q="):
                real_url = href.split("/url?q=")[1].split("&")[0]
                if real_url.startswith("http") and "google.com" not in real_url:
                    links.append(real_url)
                    if len(links) >= num_results:
                        break
        return links
    except Exception as e:
        print(f"Lỗi Google search: {e}")
        return []


def scrape_page(url):
    """Scrape nội dung từ URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        # Lấy title
        title = soup.title.string if soup.title else ""

        # Lấy nội dung từ các thẻ p
        paragraphs = soup.find_all("p")
        content = "\n".join(
            p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50
        )

        if len(content) < 200:
            return None

        return {
            "title": title.strip() if title else "Unknown",
            "content": content,
            "url": url,
            "source": "web"
        }
    except Exception as e:
        print(f"Lỗi scrape {url}: {e}")
        return None