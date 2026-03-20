"""
Đồng bộ dữ liệu runtime lên Hugging Face Dataset repo để dữ liệu bền vững.

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
from datetime import datetime, timezone

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


def _spawn_sync(task) -> None:
    """Chạy tác vụ sync trong background thread."""
    thread = threading.Thread(target=task, daemon=True)
    thread.start()


def _upload_manifest(repo: str, token: str, revision: str, include_pdf: bool, include_vector: bool) -> None:
    """Cập nhật manifest.json cơ bản trong dataset repo."""
    try:
        from huggingface_hub import HfApi
        import json
        import tempfile

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "includes": {
                "chatbot_db": True,
                "pdf": include_pdf,
                "csdl_vector": include_vector,
            },
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            temp_manifest = f.name

        try:
            api = HfApi(token=token)
            api.upload_file(
                path_or_fileobj=temp_manifest,
                path_in_repo="manifest.json",
                repo_id=repo,
                repo_type="dataset",
                revision=revision,
                commit_message="Auto-update manifest",
            )
        finally:
            try:
                os.remove(temp_manifest)
            except OSError:
                pass
    except Exception as exc:
        print(f"[DB_SYNC] Manifest update failed: {exc}")


def schedule_pdf_upload(local_pdf_path: str, remote_filename: str | None = None) -> None:
    """Upload 1 file PDF mới/chỉnh sửa lên dataset repo tại pdf/<filename>."""
    config = _get_config()
    if not config:
        return
    if not os.path.exists(local_pdf_path):
        return

    repo, token, revision = config
    remote_name = remote_filename or os.path.basename(local_pdf_path)

    def _task():
        with _lock:
            try:
                from huggingface_hub import HfApi
                api = HfApi(token=token)
                api.upload_file(
                    path_or_fileobj=local_pdf_path,
                    path_in_repo=f"pdf/{remote_name}",
                    repo_id=repo,
                    repo_type="dataset",
                    revision=revision,
                    commit_message=f"Auto-sync PDF: {remote_name}",
                )
                _upload_manifest(repo, token, revision, include_pdf=True, include_vector=False)
                print(f"[DB_SYNC] Uploaded pdf/{remote_name} to {repo}")
            except Exception as exc:
                print(f"[DB_SYNC] PDF upload failed: {exc}")

    _spawn_sync(_task)


def schedule_pdf_delete(remote_filename: str) -> None:
    """Xóa 1 file PDF từ dataset repo tại pdf/<filename>."""
    config = _get_config()
    if not config or not remote_filename:
        return
    repo, token, revision = config

    def _task():
        with _lock:
            try:
                from huggingface_hub import HfApi
                api = HfApi(token=token)
                api.delete_file(
                    path_in_repo=f"pdf/{remote_filename}",
                    repo_id=repo,
                    repo_type="dataset",
                    revision=revision,
                    commit_message=f"Auto-remove PDF: {remote_filename}",
                )
                _upload_manifest(repo, token, revision, include_pdf=True, include_vector=False)
                print(f"[DB_SYNC] Deleted pdf/{remote_filename} from {repo}")
            except Exception as exc:
                print(f"[DB_SYNC] PDF delete failed: {exc}")

    _spawn_sync(_task)


def schedule_vector_sync() -> None:
    """Upload toàn bộ thư mục csdl_vector lên dataset repo."""
    config = _get_config()
    if not config:
        return
    from backend.runtime_paths import VECTOR_DIR

    if not os.path.isdir(VECTOR_DIR):
        return

    repo, token, revision = config

    def _task():
        with _lock:
            try:
                from huggingface_hub import HfApi
                api = HfApi(token=token)
                api.upload_folder(
                    folder_path=VECTOR_DIR,
                    path_in_repo="csdl_vector",
                    repo_id=repo,
                    repo_type="dataset",
                    revision=revision,
                    commit_message="Auto-sync vector store",
                )
                _upload_manifest(repo, token, revision, include_pdf=True, include_vector=True)
                print(f"[DB_SYNC] Uploaded csdl_vector to {repo}")
            except Exception as exc:
                print(f"[DB_SYNC] Vector sync failed: {exc}")

    _spawn_sync(_task)


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

    _spawn_sync(_sync)
