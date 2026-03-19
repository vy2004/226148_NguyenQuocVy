"""
Đồng bộ chatbot.db lên Hugging Face Dataset repo để dữ liệu bền vững.

Chỉ hoạt động khi chạy trên HF Space và có cấu hình:
  - HF_DATASET_REPO
  - HF_TOKEN
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import threading
import time

_lock = threading.Lock()
_last_sync: float = 0
_MIN_INTERVAL = 30  # tối thiểu 30 giây giữa 2 lần sync


def _get_config() -> tuple[str, str, str] | None:
    repo = os.getenv("HF_DATASET_REPO", "").strip()
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if not repo or not token:
        return None
    revision = os.getenv("HF_DATASET_REVISION", "main").strip() or "main"
    return repo, token, revision


def _safe_copy_db(db_path: str, dest: str) -> bool:
    """Tạo bản sao sạch của SQLite (checkpoint WAL trước khi copy)."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
    except Exception:
        pass

    try:
        shutil.copy2(db_path, dest)
        return True
    except Exception as e:
        print(f"[DB_SYNC] Copy failed: {e}")
        return False


def _do_upload(db_path: str, repo: str, token: str, revision: str) -> bool:
    """Upload chatbot.db lên dataset repo."""
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)

        tmp_path = db_path + ".sync_copy"
        if not _safe_copy_db(db_path, tmp_path):
            return False

        api.upload_file(
            path_or_fileobj=tmp_path,
            path_in_repo="chatbot.db",
            repo_id=repo,
            repo_type="dataset",
            revision=revision,
            commit_message="Auto-sync chatbot.db",
        )

        try:
            os.remove(tmp_path)
        except OSError:
            pass

        print(f"[DB_SYNC] Uploaded chatbot.db to {repo}")
        return True

    except Exception as e:
        print(f"[DB_SYNC] Upload failed: {e}")
        return False


def schedule_sync(db_path: str | None = None) -> None:
    """
    Lên lịch đồng bộ DB lên dataset repo (chạy background, có rate-limit).
    Gọi hàm này sau mỗi lần ghi quan trọng vào DB.
    """
    global _last_sync

    config = _get_config()
    if not config:
        return

    now = time.time()
    if now - _last_sync < _MIN_INTERVAL:
        return

    if db_path is None:
        from backend.runtime_paths import DB_PATH
        db_path = DB_PATH

    if not os.path.exists(db_path):
        return

    repo, token, revision = config

    def _sync():
        global _last_sync
        with _lock:
            if time.time() - _last_sync < _MIN_INTERVAL:
                return
            _last_sync = time.time()
            _do_upload(db_path, repo, token, revision)

    thread = threading.Thread(target=_sync, daemon=True)
    thread.start()
