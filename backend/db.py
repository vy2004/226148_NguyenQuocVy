"""
Module db: SQLite persistence layer cho chatbot.
Lưu trữ conversations và messages vào data/chatbot.db
"""

import os
import json
import sqlite3
import time
from datetime import datetime

# Đường dẫn database
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, "data", "chatbot.db")


def _get_connection():
    """Tạo kết nối SQLite."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Khởi tạo database schema."""
    conn = _get_connection()
    try:
        # Tạo bảng nguoi_dung và khoi_phuc_mat_khau
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS nguoi_dung (
                ma_nguoi_dung TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                mat_khau_bam TEXT,
                ten_hien_thi TEXT NOT NULL DEFAULT 'Người dùng',
                phuong_thuc_dang_nhap TEXT NOT NULL DEFAULT 'email',
                ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS khoi_phuc_mat_khau (
                ma_khoi_phuc INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                ma_otp TEXT NOT NULL,
                thoi_gian_het_han TIMESTAMP NOT NULL,
                da_su_dung INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS cuoc_tro_chuyen (
                ma_cuoc_tro_chuyen TEXT PRIMARY KEY,
                ma_nguoi_dung TEXT,
                tieu_de TEXT NOT NULL DEFAULT 'Cuộc trò chuyện mới',
                ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ma_nguoi_dung) REFERENCES nguoi_dung(ma_nguoi_dung) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tin_nhan (
                ma_tin_nhan INTEGER PRIMARY KEY AUTOINCREMENT,
                ma_cuoc_tro_chuyen TEXT NOT NULL,
                vai_tro TEXT NOT NULL,
                noi_dung TEXT NOT NULL,
                nguon_tham_khao TEXT DEFAULT '[]',
                danh_gia TEXT DEFAULT '{}',
                ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ma_cuoc_tro_chuyen) REFERENCES cuoc_tro_chuyen(ma_cuoc_tro_chuyen) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_tin_nhan_ma_cuoc_tro_chuyen
                ON tin_nhan(ma_cuoc_tro_chuyen);
                
            CREATE INDEX IF NOT EXISTS idx_cuoc_tro_chuyen_ma_nguoi_dung
                ON cuoc_tro_chuyen(ma_nguoi_dung);
        """)

        conn.commit()
        print(f"[DB] ✅ Database initialized: {DB_PATH}")
    finally:
        conn.close()


def save_conversation(ma_cuoc_tro_chuyen: str, tieu_de: str = "Cuộc trò chuyện mới", ma_nguoi_dung: str = None):
    """Lưu hoặc cập nhật conversation."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO cuoc_tro_chuyen (ma_cuoc_tro_chuyen, tieu_de, ma_nguoi_dung) VALUES (?, ?, ?)
               ON CONFLICT(ma_cuoc_tro_chuyen) DO UPDATE SET tieu_de = excluded.tieu_de""",
            (ma_cuoc_tro_chuyen, tieu_de, ma_nguoi_dung),
        )
        conn.commit()
    finally:
        conn.close()


def save_message(ma_cuoc_tro_chuyen: str, vai_tro: str, noi_dung: str,
                 nguon_tham_khao: list = None, danh_gia: dict = None):
    """Lưu một message vào database."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO tin_nhan (ma_cuoc_tro_chuyen, vai_tro, noi_dung, nguon_tham_khao, danh_gia)
               VALUES (?, ?, ?, ?, ?)""",
            (
                ma_cuoc_tro_chuyen,
                vai_tro,
                noi_dung,
                json.dumps(nguon_tham_khao or [], ensure_ascii=False),
                json.dumps(danh_gia or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_conversation_title(ma_cuoc_tro_chuyen: str, tieu_de: str):
    """Cập nhật tiêu đề conversation."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE cuoc_tro_chuyen SET tieu_de = ? WHERE ma_cuoc_tro_chuyen = ?",
            (tieu_de, ma_cuoc_tro_chuyen),
        )
        conn.commit()
    finally:
        conn.close()


def load_all_conversations(ma_nguoi_dung: str = None) -> dict:
    """
    Load tất cả conversations và messages từ DB.
    Nếu ma_nguoi_dung được cung cấp, chỉ load conversations của user đó.
    Returns: dict {ma_cuoc_tro_chuyen: {"title": ..., "messages": [...]}}
    """
    conn = _get_connection()
    try:
        conversations = {}

        # Load conversations
        if ma_nguoi_dung:
            rows = conn.execute(
                "SELECT ma_cuoc_tro_chuyen, tieu_de, ngay_tao FROM cuoc_tro_chuyen WHERE ma_nguoi_dung = ? ORDER BY ngay_tao DESC",
                (ma_nguoi_dung,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ma_cuoc_tro_chuyen, tieu_de, ngay_tao FROM cuoc_tro_chuyen ORDER BY ngay_tao DESC"
            ).fetchall()

        for row in rows:
            ma_cuoc_tro_chuyen = row["ma_cuoc_tro_chuyen"]
            conversations[ma_cuoc_tro_chuyen] = {
                "title": row["tieu_de"],
                "messages": [],
            }

        # Load messages
        if conversations:
            conv_ids = list(conversations.keys())
            placeholders = ",".join(["?"] * len(conv_ids))
            msg_rows = conn.execute(
                f"""SELECT ma_cuoc_tro_chuyen, vai_tro, noi_dung, nguon_tham_khao, danh_gia
                   FROM tin_nhan WHERE ma_cuoc_tro_chuyen IN ({placeholders}) ORDER BY ma_tin_nhan ASC""",
                conv_ids
            ).fetchall()
        else:
            msg_rows = []

        for msg in msg_rows:
            ma_cuoc_tro_chuyen = msg["ma_cuoc_tro_chuyen"]
            if ma_cuoc_tro_chuyen not in conversations:
                continue

            message = {
                "role": msg["vai_tro"],
                "content": msg["noi_dung"],
            }

            # Parse sources JSON
            try:
                sources = json.loads(msg["nguon_tham_khao"] or "[]")
                if sources:
                    message["sources"] = sources
            except (json.JSONDecodeError, TypeError):
                pass

            # Parse evaluation JSON
            try:
                evaluation = json.loads(msg["danh_gia"] or "{}")
                if evaluation:
                    message["evaluation"] = evaluation
            except (json.JSONDecodeError, TypeError):
                pass

            conversations[ma_cuoc_tro_chuyen]["messages"].append(message)

        print(f"[DB] ✅ Loaded {len(conversations)} conversations")
        return conversations

    finally:
        conn.close()


def load_messages(ma_cuoc_tro_chuyen: str) -> list:
    """Load messages cho một conversation cụ thể."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT vai_tro, noi_dung, nguon_tham_khao, danh_gia
               FROM tin_nhan WHERE ma_cuoc_tro_chuyen = ? ORDER BY ma_tin_nhan ASC""",
            (ma_cuoc_tro_chuyen,),
        ).fetchall()

        messages = []
        for msg in rows:
            message = {"role": msg["vai_tro"], "content": msg["noi_dung"]}
            try:
                sources = json.loads(msg["nguon_tham_khao"] or "[]")
                if sources:
                    message["sources"] = sources
            except (json.JSONDecodeError, TypeError):
                pass
            try:
                evaluation = json.loads(msg["danh_gia"] or "{}")
                if evaluation:
                    message["evaluation"] = evaluation
            except (json.JSONDecodeError, TypeError):
                pass
            messages.append(message)

        return messages
    finally:
        conn.close()


def delete_conversation(ma_cuoc_tro_chuyen: str):
    """Xóa conversation và tất cả messages liên quan."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM cuoc_tro_chuyen WHERE ma_cuoc_tro_chuyen = ?", (ma_cuoc_tro_chuyen,))
        conn.commit()
        print(f"[DB] 🗑️ Deleted conversation: {ma_cuoc_tro_chuyen}")
    finally:
        conn.close()


# Khởi tạo DB khi import module
init_db()
