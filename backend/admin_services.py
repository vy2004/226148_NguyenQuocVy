"""
Admin Service Layer: Tài liệu hệ thống, User, History, Feedback, RAG thống kê/reindex.
Dùng cho trang quản trị Admin.
"""

import os
import sys
import uuid
import shutil

# Đảm bảo import được data_processing (từ thư mục gốc project)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend import db
from backend.auth import is_admin
from backend.runtime_paths import PDF_DIR
from backend.db_sync import schedule_pdf_upload, schedule_pdf_delete, schedule_vector_sync
from data_processing.dynamic_indexing import add_pdf_file
from data_processing.indexing import delete_chunks_by_source


# ======================== UserService ========================

def list_users(limit: int = 500) -> list:
    """Danh sách người dùng (admin)."""
    return db.list_users(limit=limit)


def update_user_role(ma_nguoi_dung: str, vai_tro: str) -> tuple[bool, str]:
    """Cập nhật vai trò (user/admin). Returns (success, message)."""
    if vai_tro not in ("user", "admin"):
        return False, "Vai trò không hợp lệ"
    ok = db.update_user_role(ma_nguoi_dung, vai_tro)
    return ok, "Đã cập nhật vai trò" if ok else "Cập nhật thất bại"


def lock_user(ma_nguoi_dung: str) -> bool:
    """Khóa tài khoản."""
    return db.lock_user(ma_nguoi_dung)


def unlock_user(ma_nguoi_dung: str) -> bool:
    """Mở khóa tài khoản."""
    return db.unlock_user(ma_nguoi_dung)


# ======================== HistoryService ========================

def list_conversations(limit: int = 200) -> list:
    """Lịch sử hỏi đáp toàn hệ thống (admin)."""
    return db.list_conversations_admin(limit=limit)


def list_feedback(limit: int = 300) -> list:
    """Danh sách phản hồi người dùng (admin)."""
    return db.list_feedback_admin(limit=limit)


def update_feedback_status(ma_phan_hoi: int, trang_thai: str) -> tuple[bool, str]:
    """Cập nhật trạng thái xử lý phản hồi: moi / daxem / dong."""
    if trang_thai not in ("moi", "daxem", "dong"):
        return False, "Trạng thái không hợp lệ"
    ok = db.update_phan_hoi_status(ma_phan_hoi, trang_thai)
    return ok, "Đã cập nhật" if ok else "Cập nhật thất bại"


# ======================== Tài liệu hệ thống (DocumentService) ========================


def list_system_docs() -> list:
    """
    Danh sách tài liệu hệ thống: từ bảng tai_lieu_he_thong (nếu có)
    và/hoặc quét thư mục PDF runtime để đồng bộ.
    """
    from backend.db import list_tai_lieu_he_thong
    rows = list_tai_lieu_he_thong()
    # Bổ sung từ thư mục PDF runtime nếu file tồn tại nhưng chưa trong DB
    os.makedirs(PDF_DIR, exist_ok=True)
    for f in os.listdir(PDF_DIR):
        if f.lower().endswith(".pdf"):
            path = os.path.join(PDF_DIR, f)
            path_norm = os.path.normpath(path)
            if not any(os.path.normpath(r["duong_dan"]) == path_norm for r in rows):
                rows.append({
                    "ma_tai_lieu": f"file_{os.path.splitext(f)[0]}",
                    "ten_file": f,
                    "duong_dan": path_norm,
                    "ngay_them": None,
                    "ngay_cap_nhat": None,
                })
    return rows


def create_system_doc(file_path: str, filename: str = None) -> tuple[bool, str]:
    """
    Thêm tài liệu hệ thống: copy file vào thư mục PDF runtime và ghi DB.
    file_path: đường dẫn file tải lên (Streamlit UploadedFile hoặc path).
    """
    filename = filename or os.path.basename(file_path)
    if not filename.lower().endswith(".pdf"):
        return False, "Chỉ chấp nhận file PDF"
    ma = str(uuid.uuid4())
    dest = os.path.join(PDF_DIR, filename)
    os.makedirs(PDF_DIR, exist_ok=True)
    try:
        if hasattr(file_path, "read"):
            with open(dest, "wb") as f:
                f.write(file_path.read())
        else:
            shutil.copy2(file_path, dest)
        db.insert_tai_lieu_he_thong(ma_tai_lieu=ma, ten_file=filename, duong_dan=os.path.abspath(dest))
        # Index ngay sau khi upload để hỏi đáp dùng được luôn.
        chunks_added = add_pdf_file(dest)
        schedule_pdf_upload(dest, filename)
        return True, f"Đã thêm tài liệu và index {chunks_added} chunks."
    except Exception as e:
        return False, str(e)


def update_system_doc(ma_tai_lieu: str, file_path: str = None, ten_file: str = None) -> tuple[bool, str]:
    """Cập nhật tài liệu hệ thống (metadata hoặc thay file)."""
    docs = [r for r in list_system_docs() if r.get("ma_tai_lieu") == ma_tai_lieu]
    if not docs:
        return False, "Không tìm thấy tài liệu"
    old_path = docs[0].get("duong_dan")
    new_name = ten_file or (os.path.basename(file_path) if file_path else docs[0]["ten_file"])
    if file_path and os.path.exists(old_path):
        try:
            if hasattr(file_path, "read"):
                with open(old_path, "wb") as f:
                    f.write(file_path.read())
            else:
                shutil.copy2(file_path, old_path)
        except Exception as e:
            return False, str(e)
    # Cập nhật tên trong DB nếu đổi tên (cần hàm update trong db - hiện chỉ có insert upsert)
    db.insert_tai_lieu_he_thong(ma_tai_lieu=ma_tai_lieu, ten_file=new_name, duong_dan=old_path)
    # Khi thay file, cần cập nhật vector ngay để tránh dùng dữ liệu cũ.
    if file_path:
        delete_chunks_by_source(new_name)
        chunks_added = add_pdf_file(old_path)
        msg = f"Đã cập nhật và index lại {chunks_added} chunks."
    else:
        msg = "Đã cập nhật metadata tài liệu."
    schedule_pdf_upload(old_path, new_name)
    return True, msg


def delete_system_doc(ma_tai_lieu: str) -> tuple[bool, str]:
    """Xóa tài liệu hệ thống: xóa file (nếu có) và xóa bản ghi DB."""
    docs = [r for r in list_system_docs() if r.get("ma_tai_lieu") == ma_tai_lieu]
    if not docs:
        return False, "Không tìm thấy tài liệu"
    path = docs[0].get("duong_dan")
    filename = docs[0].get("ten_file") or (os.path.basename(path) if path else "")
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
    db.delete_tai_lieu_he_thong(ma_tai_lieu)
    if filename:
        schedule_pdf_delete(filename)
    return True, "Đã xóa tài liệu. Chạy 'Tái lập chỉ mục' để cập nhật RAG."


def reindex_doc(ma_tai_lieu: str) -> tuple[bool, str]:
    """Tái lập chỉ mục cho một tài liệu (reindex toàn bộ vẫn an toàn hơn)."""
    # Đơn giản: gọi reindex_all (ChromaDB không hỗ trợ xóa theo source dễ dàng)
    return reindex_all()


def reindex_all() -> tuple[bool, str]:
    """Tái lập chỉ mục Vector DB: chạy pipeline đọc PDF → chunk → ChromaDB."""
    try:
        from data_processing.loader import load_all_documents
        from data_processing.chunking import chunk_documents
        from data_processing.indexing import create_vector_database, delete_collection
        documents = load_all_documents(PDF_DIR)
        if not documents:
            return False, f"Không có tài liệu PDF trong {PDF_DIR}"
        chunks = chunk_documents(documents)
        try:
            delete_collection()
        except Exception:
            pass
        create_vector_database(chunks)
        schedule_vector_sync()
        return True, f"Đã tái lập chỉ mục: {len(documents)} tài liệu, {len(chunks)} chunks."
    except Exception as e:
        return False, f"Lỗi: {str(e)}"


# ======================== RAGAdminService ========================

def get_rag_stats() -> dict:
    """Thống kê RAG (ChromaDB)."""
    try:
        from data_processing.indexing import get_stats
        return get_stats()
    except Exception as e:
        return {"error": str(e), "total_chunks": 0, "collection_name": ""}
