"""
Module db: SQLite persistence layer cho chatbot.
Lưu trữ conversations và messages vào thư mục dữ liệu runtime.
"""
import os
import json
import sqlite3
import time
from datetime import datetime
from backend.runtime_paths import DB_PATH


def _get_connection():
    """Tạo kết nối SQLite."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _column_exists(conn, table: str, column: str) -> bool:
    """Kiểm tra cột đã tồn tại trong bảng chưa (SQLite)."""
    row = conn.execute(
        "SELECT 1 FROM pragma_table_info(?) WHERE name = ?", (table, column)
    ).fetchone()
    return row is not None


def _table_exists(conn, table: str) -> bool:
    """Kiểm tra bảng đã tồn tại chưa (SQLite)."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


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
                ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS khoi_phuc_mat_khau (
                ma_khoi_phuc INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                ma_otp TEXT NOT NULL,
                thoi_gian_het_han TIMESTAMP NOT NULL,
                da_su_dung INTEGER DEFAULT 0,
                FOREIGN KEY (email) REFERENCES nguoi_dung(email) ON DELETE CASCADE
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

            CREATE TABLE IF NOT EXISTS tai_lieu (
                ma_tai_lieu TEXT PRIMARY KEY,
                ma_nguoi_dung TEXT,
                ten_file TEXT NOT NULL,
                duong_dan TEXT NOT NULL,
                loai_tai_lieu TEXT NOT NULL DEFAULT 'user',
                trang_thai TEXT NOT NULL DEFAULT 'hoan_thanh',
                ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ngay_cap_nhat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ma_nguoi_dung) REFERENCES nguoi_dung(ma_nguoi_dung) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS phan_hoi_nguoi_dung (
                ma_phan_hoi INTEGER PRIMARY KEY AUTOINCREMENT,
                ma_tin_nhan INTEGER NOT NULL,
                ma_nguoi_dung TEXT,
                loai TEXT NOT NULL DEFAULT 'thich',
                noi_dung_phan_hoi TEXT DEFAULT '',
                ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ma_tin_nhan) REFERENCES tin_nhan(ma_tin_nhan) ON DELETE CASCADE,
                FOREIGN KEY (ma_nguoi_dung) REFERENCES nguoi_dung(ma_nguoi_dung) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tin_nhan_ma_cuoc_tro_chuyen
                ON tin_nhan(ma_cuoc_tro_chuyen);
                
            CREATE INDEX IF NOT EXISTS idx_cuoc_tro_chuyen_ma_nguoi_dung
                ON cuoc_tro_chuyen(ma_nguoi_dung);

            CREATE INDEX IF NOT EXISTS idx_tai_lieu_ma_nguoi_dung
                ON tai_lieu(ma_nguoi_dung);

            CREATE INDEX IF NOT EXISTS idx_tai_lieu_loai
                ON tai_lieu(loai_tai_lieu);

            CREATE INDEX IF NOT EXISTS idx_phan_hoi_ma_tin_nhan
                ON phan_hoi_nguoi_dung(ma_tin_nhan);

            CREATE INDEX IF NOT EXISTS idx_phan_hoi_ma_nguoi_dung
                ON phan_hoi_nguoi_dung(ma_nguoi_dung);

            CREATE TABLE IF NOT EXISTS tin_nhan_tham_khao (
                ma_tham_khao INTEGER PRIMARY KEY AUTOINCREMENT,
                ma_tin_nhan INTEGER NOT NULL,
                ma_tai_lieu TEXT,
                nguon TEXT NOT NULL,
                diem REAL,
                chunk_index INTEGER,
                ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ma_tin_nhan) REFERENCES tin_nhan(ma_tin_nhan) ON DELETE CASCADE,
                FOREIGN KEY (ma_tai_lieu) REFERENCES tai_lieu(ma_tai_lieu) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tham_khao_ma_tin_nhan
                ON tin_nhan_tham_khao(ma_tin_nhan);
            CREATE INDEX IF NOT EXISTS idx_tham_khao_ma_tai_lieu
                ON tin_nhan_tham_khao(ma_tai_lieu);
        """)

        # Migration: thêm vai_tro, khoa_tai_khoan vào nguoi_dung (nếu chưa có)
        if not _column_exists(conn, "nguoi_dung", "vai_tro"):
            conn.execute("ALTER TABLE nguoi_dung ADD COLUMN vai_tro TEXT NOT NULL DEFAULT 'user'")
            print("[DB] Migration: added nguoi_dung.vai_tro")
        if not _column_exists(conn, "nguoi_dung", "khoa_tai_khoan"):
            conn.execute("ALTER TABLE nguoi_dung ADD COLUMN khoa_tai_khoan INTEGER NOT NULL DEFAULT 0")
            print("[DB] Migration: added nguoi_dung.khoa_tai_khoan")

        # Migration: thêm trang_thai_xu_ly vào phan_hoi_nguoi_dung (nếu chưa có)
        if not _column_exists(conn, "phan_hoi_nguoi_dung", "trang_thai_xu_ly"):
            conn.execute("ALTER TABLE phan_hoi_nguoi_dung ADD COLUMN trang_thai_xu_ly TEXT DEFAULT 'moi'")
            print("[DB] Migration: added phan_hoi_nguoi_dung.trang_thai_xu_ly")

        # Migration: tạo bảng tin_nhan_tham_khao nếu thiếu (db cũ)
        if not _table_exists(conn, "tin_nhan_tham_khao"):
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tin_nhan_tham_khao (
                    ma_tham_khao INTEGER PRIMARY KEY AUTOINCREMENT,
                    ma_tin_nhan INTEGER NOT NULL,
                    ma_tai_lieu TEXT,
                    nguon TEXT NOT NULL,
                    diem REAL,
                    chunk_index INTEGER,
                    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ma_tin_nhan) REFERENCES tin_nhan(ma_tin_nhan) ON DELETE CASCADE,
                    FOREIGN KEY (ma_tai_lieu) REFERENCES tai_lieu(ma_tai_lieu) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tham_khao_ma_tin_nhan
                    ON tin_nhan_tham_khao(ma_tin_nhan);
                CREATE INDEX IF NOT EXISTS idx_tham_khao_ma_tai_lieu
                    ON tin_nhan_tham_khao(ma_tai_lieu);
            """)
            print("[DB] Migration: created tin_nhan_tham_khao")

        # Migration: gộp tai_lieu_nguoi_dung + tai_lieu_he_thong → tai_lieu
        if _table_exists(conn, "tai_lieu_nguoi_dung") or _table_exists(conn, "tai_lieu_he_thong"):
            if _table_exists(conn, "tai_lieu_nguoi_dung"):
                conn.execute("""
                    INSERT OR IGNORE INTO tai_lieu
                        (ma_tai_lieu, ma_nguoi_dung, ten_file, duong_dan, loai_tai_lieu, trang_thai, ngay_tao)
                    SELECT ma_tai_lieu, ma_nguoi_dung, ten_file, duong_dan, 'user', trang_thai, ngay_tai_len
                    FROM tai_lieu_nguoi_dung
                """)
                conn.execute("DROP TABLE tai_lieu_nguoi_dung")
                print("[DB] Migration: merged tai_lieu_nguoi_dung → tai_lieu")

            if _table_exists(conn, "tai_lieu_he_thong"):
                conn.execute("""
                    INSERT OR IGNORE INTO tai_lieu
                        (ma_tai_lieu, ten_file, duong_dan, loai_tai_lieu, trang_thai, ngay_tao, ngay_cap_nhat)
                    SELECT ma_tai_lieu, ten_file, duong_dan, 'admin', 'hoan_thanh', ngay_them, ngay_cap_nhat
                    FROM tai_lieu_he_thong
                """)
                conn.execute("DROP TABLE tai_lieu_he_thong")
                print("[DB] Migration: merged tai_lieu_he_thong → tai_lieu")

            # Cập nhật FK của tin_nhan_tham_khao → tai_lieu
            if _table_exists(conn, "tin_nhan_tham_khao"):
                conn.executescript("""
                    CREATE TABLE tin_nhan_tham_khao_new (
                        ma_tham_khao INTEGER PRIMARY KEY AUTOINCREMENT,
                        ma_tin_nhan INTEGER NOT NULL,
                        ma_tai_lieu TEXT,
                        nguon TEXT NOT NULL,
                        diem REAL,
                        chunk_index INTEGER,
                        ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (ma_tin_nhan) REFERENCES tin_nhan(ma_tin_nhan) ON DELETE CASCADE,
                        FOREIGN KEY (ma_tai_lieu) REFERENCES tai_lieu(ma_tai_lieu) ON DELETE SET NULL
                    );
                    INSERT INTO tin_nhan_tham_khao_new SELECT * FROM tin_nhan_tham_khao;
                    DROP TABLE tin_nhan_tham_khao;
                    ALTER TABLE tin_nhan_tham_khao_new RENAME TO tin_nhan_tham_khao;
                    CREATE INDEX IF NOT EXISTS idx_tham_khao_ma_tin_nhan ON tin_nhan_tham_khao(ma_tin_nhan);
                    CREATE INDEX IF NOT EXISTS idx_tham_khao_ma_tai_lieu ON tin_nhan_tham_khao(ma_tai_lieu);
                """)
                print("[DB] Migration: updated tin_nhan_tham_khao FK → tai_lieu")

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
                 nguon_tham_khao: list = None, danh_gia: dict = None) -> int:
    """Lưu một message vào database. Trả về ma_tin_nhan."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
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
        return cursor.lastrowid
    finally:
        conn.close()


def save_message_sources(ma_tin_nhan: int, sources: list):
    """
    Lưu nguồn tham khảo theo dạng chuẩn hóa vào bảng tin_nhan_tham_khao.
    sources: list[str] hoặc list[dict]. Hiện tại rag_chain_pg trả list[str] (tên file).
    """
    if not sources:
        return

    conn = _get_connection()
    try:
        for s in sources:
            if isinstance(s, dict):
                nguon = str(s.get("source") or s.get("ten_file") or s.get("name") or "").strip()
                diem = s.get("score")
                chunk_index = s.get("chunk_index")
            else:
                nguon = str(s).strip()
                diem = None
                chunk_index = None

            if not nguon:
                continue

            # Map nguon -> ma_tai_lieu (nếu có)
            row = conn.execute(
                "SELECT ma_tai_lieu FROM tai_lieu WHERE ten_file = ? LIMIT 1",
                (nguon,),
            ).fetchone()
            ma_tai_lieu = row["ma_tai_lieu"] if row else None

            conn.execute(
                """INSERT INTO tin_nhan_tham_khao (ma_tin_nhan, ma_tai_lieu, nguon, diem, chunk_index)
                   VALUES (?, ?, ?, ?, ?)""",
                (ma_tin_nhan, ma_tai_lieu, nguon, diem, chunk_index),
            )
        conn.commit()
    finally:
        conn.close()


def list_message_sources(ma_tin_nhan: int) -> list:
    """Lấy nguồn tham khảo chuẩn hóa cho một tin nhắn."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT ma_tham_khao, ma_tin_nhan, ma_tai_lieu, nguon, diem, chunk_index, ngay_tao
               FROM tin_nhan_tham_khao WHERE ma_tin_nhan = ? ORDER BY ma_tham_khao ASC""",
            (ma_tin_nhan,),
        ).fetchall()
        return [dict(r) for r in rows]
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
                f"""SELECT ma_tin_nhan, ma_cuoc_tro_chuyen, vai_tro, noi_dung, nguon_tham_khao, danh_gia
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
                "ma_tin_nhan": msg["ma_tin_nhan"],
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
            """SELECT ma_tin_nhan, vai_tro, noi_dung, nguon_tham_khao, danh_gia
               FROM tin_nhan WHERE ma_cuoc_tro_chuyen = ? ORDER BY ma_tin_nhan ASC""",
            (ma_cuoc_tro_chuyen,),
        ).fetchall()

        messages = []
        for msg in rows:
            message = {"role": msg["vai_tro"], "content": msg["noi_dung"], "ma_tin_nhan": msg["ma_tin_nhan"]}
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


# ======================== TÀI LIỆU (GỘP user + admin) ========================

def save_tai_lieu(ma_tai_lieu: str, ma_nguoi_dung: str, ten_file: str,
                  duong_dan: str, trang_thai: str = "dang_xu_ly",
                  loai_tai_lieu: str = "user"):
    """Lưu metadata tài liệu (user hoặc admin upload)."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO tai_lieu (ma_tai_lieu, ma_nguoi_dung, ten_file, duong_dan, trang_thai, loai_tai_lieu)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(ma_tai_lieu) DO UPDATE SET trang_thai = excluded.trang_thai,
               ngay_cap_nhat = CURRENT_TIMESTAMP""",
            (ma_tai_lieu, ma_nguoi_dung, ten_file, duong_dan, trang_thai, loai_tai_lieu),
        )
        conn.commit()
    finally:
        conn.close()


def update_trang_thai_tai_lieu(ma_tai_lieu: str, trang_thai: str):
    """Cập nhật trạng thái xử lý tài liệu (dang_xu_ly / hoan_thanh / loi)."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE tai_lieu SET trang_thai = ?, ngay_cap_nhat = CURRENT_TIMESTAMP WHERE ma_tai_lieu = ?",
            (trang_thai, ma_tai_lieu),
        )
        conn.commit()
    finally:
        conn.close()


def load_tai_lieu_by_user(ma_nguoi_dung: str) -> list:
    """Lấy danh sách tài liệu của một người dùng."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT ma_tai_lieu, ten_file, duong_dan, trang_thai, ngay_tao AS ngay_tai_len
               FROM tai_lieu WHERE ma_nguoi_dung = ? AND loai_tai_lieu = 'user'
               ORDER BY ngay_tao DESC""",
            (ma_nguoi_dung,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_tai_lieu(ma_tai_lieu: str):
    """Xóa một tài liệu."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM tai_lieu WHERE ma_tai_lieu = ?", (ma_tai_lieu,))
        conn.commit()
    finally:
        conn.close()


# ======================== PHẢN HỒI NGƯỜI DÙNG ========================

def save_phan_hoi(ma_tin_nhan: int, loai: str, ma_nguoi_dung: str = None,
                  noi_dung_phan_hoi: str = ""):
    """Lưu phản hồi / đánh giá của người dùng cho một tin nhắn."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO phan_hoi_nguoi_dung (ma_tin_nhan, ma_nguoi_dung, loai, noi_dung_phan_hoi)
               VALUES (?, ?, ?, ?)""",
            (ma_tin_nhan, ma_nguoi_dung, loai, noi_dung_phan_hoi),
        )
        conn.commit()
    finally:
        conn.close()


def load_phan_hoi_by_tin_nhan(ma_tin_nhan: int) -> list:
    """Lấy danh sách phản hồi cho một tin nhắn."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT ma_phan_hoi, ma_nguoi_dung, loai, noi_dung_phan_hoi, ngay_tao
               FROM phan_hoi_nguoi_dung WHERE ma_tin_nhan = ? ORDER BY ngay_tao DESC""",
            (ma_tin_nhan,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def load_phan_hoi_by_user(ma_nguoi_dung: str) -> list:
    """Lấy tất cả phản hồi của một người dùng."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT ma_phan_hoi, ma_tin_nhan, loai, noi_dung_phan_hoi, ngay_tao
               FROM phan_hoi_nguoi_dung WHERE ma_nguoi_dung = ? ORDER BY ngay_tao DESC""",
            (ma_nguoi_dung,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_phan_hoi(ma_phan_hoi: int):
    """Xóa một phản hồi."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM phan_hoi_nguoi_dung WHERE ma_phan_hoi = ?", (ma_phan_hoi,))
        conn.commit()
    finally:
        conn.close()


# ======================== ADMIN: NGƯỜI DÙNG ========================

def list_users(limit: int = 500) -> list:
    """Lấy danh sách tất cả người dùng (cho admin)."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT ma_nguoi_dung, email, ten_hien_thi, ngay_tao,
                      COALESCE(vai_tro, 'user') AS vai_tro,
                      COALESCE(khoa_tai_khoan, 0) AS khoa_tai_khoan
               FROM nguoi_dung ORDER BY ngay_tao DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_user_role(ma_nguoi_dung: str, vai_tro: str) -> bool:
    """Cập nhật vai trò người dùng (user / admin)."""
    if vai_tro not in ("user", "admin"):
        return False
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE nguoi_dung SET vai_tro = ? WHERE ma_nguoi_dung = ?",
            (vai_tro, ma_nguoi_dung),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def lock_user(ma_nguoi_dung: str) -> bool:
    """Khóa tài khoản người dùng."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE nguoi_dung SET khoa_tai_khoan = 1 WHERE ma_nguoi_dung = ?",
            (ma_nguoi_dung,),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def unlock_user(ma_nguoi_dung: str) -> bool:
    """Mở khóa tài khoản người dùng."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE nguoi_dung SET khoa_tai_khoan = 0 WHERE ma_nguoi_dung = ?",
            (ma_nguoi_dung,),
        )
        conn.commit()
        return True
    finally:
        conn.close()


# ======================== ADMIN: LỊCH SỬ HỎI ĐÁP TOÀN HỆ THỐNG ========================

def list_conversations_admin(limit: int = 200) -> list:
    """Lấy danh sách cuộc trò chuyện toàn hệ thống (cho admin)."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT c.ma_cuoc_tro_chuyen, c.tieu_de, c.ma_nguoi_dung, c.ngay_tao,
                      u.email, u.ten_hien_thi
               FROM cuoc_tro_chuyen c
               LEFT JOIN nguoi_dung u ON c.ma_nguoi_dung = u.ma_nguoi_dung
               ORDER BY c.ngay_tao DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_feedback_admin(limit: int = 300) -> list:
    """Lấy danh sách phản hồi toàn hệ thống (cho admin), kèm thông tin tin nhắn."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT p.ma_phan_hoi, p.ma_tin_nhan, p.ma_nguoi_dung, p.loai, p.noi_dung_phan_hoi,
                      p.ngay_tao, COALESCE(p.trang_thai_xu_ly, 'moi') AS trang_thai_xu_ly,
                      t.noi_dung AS noi_dung_tin_nhan, t.ma_cuoc_tro_chuyen
               FROM phan_hoi_nguoi_dung p
               JOIN tin_nhan t ON p.ma_tin_nhan = t.ma_tin_nhan
               ORDER BY p.ngay_tao DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_phan_hoi_status(ma_phan_hoi: int, trang_thai: str) -> bool:
    """Cập nhật trạng thái xử lý phản hồi (moi / daxem / dong)."""
    if trang_thai not in ("moi", "daxem", "dong"):
        return False
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE phan_hoi_nguoi_dung SET trang_thai_xu_ly = ? WHERE ma_phan_hoi = ?",
            (trang_thai, ma_phan_hoi),
        )
        conn.commit()
        return True
    finally:
        conn.close()


# ======================== ADMIN: TÀI LIỆU HỆ THỐNG ========================

def list_tai_lieu_he_thong() -> list:
    """Lấy danh sách tài liệu hệ thống (admin upload, dùng cho RAG)."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT ma_tai_lieu, ten_file, duong_dan, ngay_tao AS ngay_them, ngay_cap_nhat
               FROM tai_lieu WHERE loai_tai_lieu = 'admin' ORDER BY ngay_tao DESC"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def insert_tai_lieu_he_thong(ma_tai_lieu: str, ten_file: str, duong_dan: str):
    """Thêm một tài liệu hệ thống (admin) vào bảng."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO tai_lieu (ma_tai_lieu, ten_file, duong_dan, loai_tai_lieu, trang_thai)
               VALUES (?, ?, ?, 'admin', 'hoan_thanh')
               ON CONFLICT(ma_tai_lieu) DO UPDATE SET ten_file = excluded.ten_file,
               duong_dan = excluded.duong_dan, ngay_cap_nhat = CURRENT_TIMESTAMP""",
            (ma_tai_lieu, ten_file, duong_dan),
        )
        conn.commit()
    finally:
        conn.close()


def delete_tai_lieu_he_thong(ma_tai_lieu: str):
    """Xóa bản ghi tài liệu hệ thống."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM tai_lieu WHERE ma_tai_lieu = ?", (ma_tai_lieu,))
        conn.commit()
    finally:
        conn.close()


# Khởi tạo DB khi import module
init_db()
