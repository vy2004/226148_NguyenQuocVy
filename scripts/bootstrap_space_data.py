"""
Tải dataset runtime từ Hugging Face Dataset repo về thư mục APP_DATA_DIR.

Dataset repo dự kiến có cấu trúc:
  manifest.json
  csdl_vector/
  pdf/              # tùy chọn
  chatbot.db        # tùy chọn
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.runtime_paths import (
    APP_DATA_DIR,
    DATASET_MANIFEST_PATH,
    DB_PATH,
    PDF_DIR,
    VECTOR_DIR,
    ensure_app_dirs,
)


def _read_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _copy_tree(src: str, dst: str) -> None:
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _copy_file_if_missing(src: str, dst: str) -> None:
    if os.path.exists(src) and not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def _copy_file_always(src: str, dst: str) -> None:
    """Luôn copy file từ src sang dst (ghi đè nếu đã tồn tại)."""
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def _vector_dir_ready() -> bool:
    return os.path.isdir(VECTOR_DIR) and any(Path(VECTOR_DIR).iterdir())


def _load_remote_manifest(repo_id: str, revision: str, token: str | None) -> dict:
    try:
        manifest_path = hf_hub_download(
            repo_id=repo_id,
            repo_type="dataset",
            filename="manifest.json",
            revision=revision,
            token=token,
        )
        return _read_json(manifest_path)
    except Exception as exc:
        print(f"[BOOTSTRAP] Không tải được manifest.json: {exc}")
        return {}


def _should_sync(local_meta: dict, remote_manifest: dict, repo_id: str, revision: str, force: bool) -> bool:
    if force:
        return True
    if not _vector_dir_ready():
        return True
    if not local_meta:
        return True
    if local_meta.get("repo_id") != repo_id:
        return True
    if local_meta.get("revision") != revision:
        return True
    if local_meta.get("manifest") != remote_manifest:
        return True
    return False


def bootstrap_space_data(force: bool = False) -> bool:
    ensure_app_dirs()

    repo_id = os.getenv("HF_DATASET_REPO", "").strip()
    if not repo_id:
        print("[BOOTSTRAP] HF_DATASET_REPO chưa được cấu hình. Bỏ qua bước tải dataset.")
        return False

    revision = os.getenv("HF_DATASET_REVISION", "main").strip() or "main"
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    local_meta = _read_json(DATASET_MANIFEST_PATH)
    remote_manifest = _load_remote_manifest(repo_id, revision, token)

    if not _should_sync(local_meta, remote_manifest, repo_id, revision, force):
        print(f"[BOOTSTRAP] Dataset đã đồng bộ sẵn tại {APP_DATA_DIR}")
        return False

    print(f"[BOOTSTRAP] Đang tải dataset từ {repo_id}@{revision} ...")
    with tempfile.TemporaryDirectory(prefix="hf_dataset_") as tmp_dir:
        snapshot_dir = snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            revision=revision,
            token=token,
            local_dir=tmp_dir,
        )

        vector_src = os.path.join(snapshot_dir, "csdl_vector")
        if not os.path.isdir(vector_src):
            raise RuntimeError("Dataset repo không chứa thư mục csdl_vector/")
        _copy_tree(vector_src, VECTOR_DIR)

        pdf_src = os.path.join(snapshot_dir, "pdf")
        if os.path.isdir(pdf_src):
            _copy_tree(pdf_src, PDF_DIR)

        db_src = os.path.join(snapshot_dir, "chatbot.db")
        _copy_file_always(db_src, DB_PATH)
        print(f"[BOOTSTRAP] Đã tải chatbot.db mới nhất từ dataset repo")

    meta = {
        "repo_id": repo_id,
        "revision": revision,
        "manifest": remote_manifest,
    }
    _write_json(DATASET_MANIFEST_PATH, meta)
    print(f"[BOOTSTRAP] Hoàn tất đồng bộ dataset vào {APP_DATA_DIR}")
    return True


def main() -> int:
    force = os.getenv("HF_DATASET_FORCE_SYNC", "0") == "1"
    try:
        bootstrap_space_data(force=force)
        return 0
    except Exception as exc:
        print(f"[BOOTSTRAP] Lỗi đồng bộ dataset: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
