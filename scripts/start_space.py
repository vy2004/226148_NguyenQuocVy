"""
Entrypoint cho Hugging Face Space.
1. Tải dataset runtime nếu cần
2. Tạo thư mục dữ liệu cơ bản
3. Chạy Streamlit
"""

from __future__ import annotations

import os
import subprocess
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.runtime_paths import APP_DATA_DIR, PDF_DIR, VECTOR_DIR, ensure_app_dirs
from scripts.bootstrap_space_data import bootstrap_space_data


def main() -> int:
    ensure_app_dirs()

    dataset_required = os.getenv("HF_DATASET_REQUIRED", "0") == "1"
    try:
        bootstrap_space_data(force=os.getenv("HF_DATASET_FORCE_SYNC", "0") == "1")
    except Exception as exc:
        print(f"[SPACE] Bootstrap dataset thất bại: {exc}")
        if dataset_required:
            return 1

    print(f"[SPACE] APP_DATA_DIR = {APP_DATA_DIR}")
    print(f"[SPACE] PDF_DIR = {PDF_DIR}")
    print(f"[SPACE] VECTOR_DIR = {VECTOR_DIR}")

    cmd = [
        "streamlit",
        "run",
        "frontend/app.py",
        "--server.port=7860",
        "--server.address=0.0.0.0",
    ]
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
