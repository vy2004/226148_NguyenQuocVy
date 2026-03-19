"""
Xuất một bundle dữ liệu để đẩy lên Hugging Face Dataset repo.

Ví dụ:
python scripts/export_dataset_bundle.py --output-dir ..\\chatbot-lichsu-data --include-pdf
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.runtime_paths import APP_DATA_DIR, DB_PATH, PDF_DIR, VECTOR_DIR
from data_processing.indexing import COLLECTION_NAME, get_stats


def _copy_tree(src: str, dst: str) -> None:
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _copy_file(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def build_manifest(include_pdf: bool, include_db: bool) -> dict:
    stats = get_stats()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "app_data_dir": APP_DATA_DIR,
        "collection_name": COLLECTION_NAME,
        "total_chunks": stats.get("total_chunks", 0),
        "embedding_model": stats.get("embedding_model"),
        "includes": {
            "csdl_vector": True,
            "pdf": include_pdf,
            "chatbot_db": include_db,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export dữ liệu runtime sang bundle để push lên HF Dataset repo.")
    parser.add_argument("--output-dir", required=True, help="Thư mục output cho dataset repo.")
    parser.add_argument("--include-pdf", action="store_true", help="Sao chép thêm thư mục pdf/.")
    parser.add_argument("--include-db", action="store_true", help="Sao chép thêm chatbot.db nếu muốn seed DB.")
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.isdir(VECTOR_DIR):
        raise RuntimeError(f"Không tìm thấy thư mục vector runtime: {VECTOR_DIR}")

    _copy_tree(VECTOR_DIR, os.path.join(output_dir, "csdl_vector"))

    if args.include_pdf and os.path.isdir(PDF_DIR):
        _copy_tree(PDF_DIR, os.path.join(output_dir, "pdf"))

    if args.include_db and os.path.exists(DB_PATH):
        _copy_file(DB_PATH, os.path.join(output_dir, "chatbot.db"))

    manifest = build_manifest(args.include_pdf, args.include_db)
    with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Đã xuất dataset bundle vào: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
