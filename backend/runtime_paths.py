"""
Quản lý đường dẫn dữ liệu runtime dùng chung cho local và Hugging Face Space.
"""

from __future__ import annotations

import os


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_default_data_dir() -> str:
    """Mặc định local dùng ./data, còn Space không cấu hình thì dùng /tmp/app_data."""
    if os.getenv("SPACE_ID"):
        return "/tmp/app_data"
    return os.path.join(ROOT_DIR, "data")


DEFAULT_DATA_DIR = get_default_data_dir()


def get_app_data_dir() -> str:
    """Thư mục dữ liệu runtime. Có thể override bằng APP_DATA_DIR."""
    data_dir = os.getenv("APP_DATA_DIR", DEFAULT_DATA_DIR).strip() or DEFAULT_DATA_DIR
    return os.path.abspath(data_dir)


APP_DATA_DIR = get_app_data_dir()
PDF_DIR = os.path.join(APP_DATA_DIR, "pdf")
PROCESSED_DIR = os.path.join(APP_DATA_DIR, "processed")
VECTOR_DIR = os.path.join(APP_DATA_DIR, "csdl_vector")
DB_PATH = os.path.join(APP_DATA_DIR, "chatbot.db")
ENV_PATH = os.path.join(ROOT_DIR, ".env")
DATASET_MANIFEST_PATH = os.path.join(APP_DATA_DIR, "dataset_manifest.json")


def ensure_app_dirs() -> None:
    """Tạo các thư mục runtime cơ bản nếu chưa tồn tại."""
    for path in (APP_DATA_DIR, PDF_DIR, PROCESSED_DIR, VECTOR_DIR):
        os.makedirs(path, exist_ok=True)
