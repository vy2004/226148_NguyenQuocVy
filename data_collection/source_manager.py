"""
Quản lý nguồn dữ liệu đã crawl - tránh crawl trùng lặp.
"""

import os
import json

CRAWLED_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "crawled_sources.json"
)


def _load_crawled():
    """Đọc danh sách nguồn đã crawl."""
    if os.path.exists(CRAWLED_FILE):
        with open(CRAWLED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_crawled(sources: list):
    """Lưu danh sách nguồn đã crawl."""
    os.makedirs(os.path.dirname(CRAWLED_FILE), exist_ok=True)
    with open(CRAWLED_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)


def is_already_crawled(title: str) -> bool:
    """Kiểm tra xem nguồn đã được crawl chưa."""
    sources = _load_crawled()
    return title.lower() in [s.lower() for s in sources]


def mark_as_crawled(title: str):
    """Đánh dấu nguồn đã crawl."""
    sources = _load_crawled()
    if title not in sources:
        sources.append(title)
        _save_crawled(sources)


def get_all_crawled() -> list:
    """Lấy danh sách tất cả nguồn đã crawl."""
    return _load_crawled()