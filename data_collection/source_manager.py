"""
Quản lý nguồn đã crawl, tránh crawl trùng, đánh giá độ tin cậy.
"""
import json
import os
from datetime import datetime

CRAWL_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "crawl_log.json")

TRUSTED_DOMAINS = [
    "vi.wikipedia.org",
    "lichsuvietnam.vn",
    "nghiencuulichsu.com",
    "baotanglichsu.vn",
    "vansudia.net",
]

def load_crawl_log() -> dict:
    """Đọc log các URL đã crawl."""
    if os.path.exists(CRAWL_LOG_PATH):
        with open(CRAWL_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"crawled_urls": []}

def save_crawl_log(log: dict):
    """Lưu log."""
    os.makedirs(os.path.dirname(CRAWL_LOG_PATH), exist_ok=True)
    with open(CRAWL_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def is_already_crawled(url: str) -> bool:
    """Kiểm tra URL đã crawl chưa."""
    log = load_crawl_log()
    return url in [entry["url"] for entry in log["crawled_urls"]]

def mark_as_crawled(url: str, title: str, source: str):
    """Đánh dấu URL đã crawl xong."""
    log = load_crawl_log()
    log["crawled_urls"].append({
        "url": url,
        "title": title,
        "source": source,
        "crawled_at": datetime.now().isoformat()
    })
    save_crawl_log(log)

def is_trusted_source(url: str) -> bool:
    """Kiểm tra URL có thuộc nguồn uy tín không."""
    return any(domain in url for domain in TRUSTED_DOMAINS)

def get_crawl_stats() -> dict:
    """Thống kê số lượng đã crawl."""
    log = load_crawl_log()
    total = len(log["crawled_urls"])
    by_source = {}
    for entry in log["crawled_urls"]:
        src = entry.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1
    return {"total": total, "by_source": by_source}