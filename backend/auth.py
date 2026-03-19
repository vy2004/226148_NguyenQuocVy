"""
Module auth: Xác thực người dùng cho chatbot.
Hỗ trợ đăng ký, đăng nhập bằng email/password và quên mật khẩu.
"""

import uuid
import random
import string
import hashlib
import sqlite3
from datetime import datetime, timedelta
from backend.runtime_paths import DB_PATH


def _get_connection():
    """Tạo kết nối SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _hash_password(password: str) -> str:
    """Hash password bằng SHA-256 + salt."""
    salt = uuid.uuid4().hex
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """Kiểm tra password có khớp với hash không."""
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, hashed = stored_hash.split("$", 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == hashed


def register_user(email: str, password: str, display_name: str = None) -> dict:
    """
    Đăng ký tài khoản mới.
    Returns: {"success": True/False, "message": str, "user": dict or None}
    """
    email = email.strip().lower()
    if not email or not password:
        return {"success": False, "message": "Email và mật khẩu không được để trống"}

    # Ràng buộc định dạng email: chỉ chấp nhận địa chỉ @gmail.com
    if not email.endswith("@gmail.com"):
        return {"success": False, "message": "Vui lòng nhập địa chỉ Email hợp lệ!"}

    if len(password) < 6:
        return {"success": False, "message": "Mật khẩu phải có ít nhất 6 ký tự"}

    conn = _get_connection()
    try:
        # Kiểm tra email đã tồn tại chưa
        existing = conn.execute(
            "SELECT ma_nguoi_dung FROM nguoi_dung WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            return {"success": False, "message": "Email này đã được đăng ký"}

        user_id = str(uuid.uuid4())
        password_hash = _hash_password(password)
        name = display_name or email.split("@")[0]

        conn.execute(
            """INSERT INTO nguoi_dung (ma_nguoi_dung, email, mat_khau_bam, ten_hien_thi)
               VALUES (?, ?, ?, ?)""",
            (user_id, email, password_hash, name),
        )
        conn.commit()

        user = {
            "id": user_id,
            "email": email,
            "display_name": name,
        }
        print(f"[AUTH] ✅ Đăng ký thành công: {email}")
        return {"success": True, "message": "Đăng ký thành công!", "user": user}

    except Exception as e:
        print(f"[AUTH] ❌ Lỗi đăng ký: {e}")
        return {"success": False, "message": f"Lỗi hệ thống: {str(e)}"}
    finally:
        conn.close()


def login_user(email: str, password: str) -> dict:
    """
    Đăng nhập bằng email/password.
    Returns: {"success": True/False, "message": str, "user": dict or None}
    User dict gồm: id, email, display_name, role ('user'|'admin').
    """
    email = email.strip().lower()
    conn = _get_connection()
    try:
        row = conn.execute(
            """SELECT ma_nguoi_dung, email, mat_khau_bam, ten_hien_thi,
                      COALESCE(vai_tro, 'user') AS vai_tro,
                      COALESCE(khoa_tai_khoan, 0) AS khoa_tai_khoan
               FROM nguoi_dung WHERE email = ?""",
            (email,),
        ).fetchone()

        if not row:
            return {"success": False, "message": "Email không tồn tại"}

        if row["khoa_tai_khoan"]:
            return {"success": False, "message": "Tài khoản đã bị khóa. Liên hệ quản trị viên."}

        if not _verify_password(password, row["mat_khau_bam"]):
            return {"success": False, "message": "Mật khẩu không đúng"}

        user = {
            "id": row["ma_nguoi_dung"],
            "email": row["email"],
            "display_name": row["ten_hien_thi"],
            "role": row["vai_tro"] if row["vai_tro"] else "user",
        }
        print(f"[AUTH] ✅ Đăng nhập: {email} (role={user['role']})")
        return {"success": True, "message": "Đăng nhập thành công!", "user": user}

    finally:
        conn.close()


def is_admin(user: dict) -> bool:
    """Kiểm tra user có phải admin không."""
    return user and user.get("role") == "admin"


def create_reset_token(email: str) -> dict:
    """
    Tạo mã OTP reset password (6 chữ số, hết hạn 15 phút).
    Returns: {"success": True/False, "message": str, "token": str or None}
    """
    email = email.strip().lower()
    conn = _get_connection()
    try:
        # Kiểm tra email tồn tại
        row = conn.execute(
            "SELECT ma_nguoi_dung FROM nguoi_dung WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            return {"success": False, "message": "Email không tồn tại trong hệ thống"}

        # Tạo OTP 6 chữ số
        token = "".join(random.choices(string.digits, k=6))
        expires_at = (datetime.now() + timedelta(minutes=15)).isoformat()

        # Xóa token cũ (nếu có)
        conn.execute("DELETE FROM khoi_phuc_mat_khau WHERE email = ?", (email,))
        conn.execute(
            "INSERT INTO khoi_phuc_mat_khau (email, ma_otp, thoi_gian_het_han) VALUES (?, ?, ?)",
            (email, token, expires_at),
        )
        conn.commit()

        print(f"[AUTH] 🔑 Reset token created for: {email}")
        return {"success": True, "message": "Mã OTP đã được tạo", "token": token}

    finally:
        conn.close()


def reset_password(email: str, token: str, new_password: str) -> dict:
    """
    Đặt lại mật khẩu bằng mã OTP.
    Returns: {"success": True/False, "message": str}
    """
    email = email.strip().lower()
    if len(new_password) < 6:
        return {"success": False, "message": "Mật khẩu mới phải có ít nhất 6 ký tự"}

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT ma_otp, thoi_gian_het_han, da_su_dung FROM khoi_phuc_mat_khau WHERE email = ? ORDER BY ma_khoi_phuc DESC LIMIT 1",
            (email,),
        ).fetchone()

        if not row:
            return {"success": False, "message": "Không tìm thấy yêu cầu đặt lại mật khẩu"}

        if row["da_su_dung"]:
            return {"success": False, "message": "Mã OTP đã được sử dụng"}

        if row["ma_otp"] != token:
            return {"success": False, "message": "Mã OTP không đúng"}

        # Kiểm tra hết hạn
        expires_at = datetime.fromisoformat(row["thoi_gian_het_han"])
        if datetime.now() > expires_at:
            return {"success": False, "message": "Mã OTP đã hết hạn (15 phút)"}

        # Cập nhật mật khẩu
        password_hash = _hash_password(new_password)
        conn.execute(
            "UPDATE nguoi_dung SET mat_khau_bam = ? WHERE email = ?",
            (password_hash, email),
        )
        conn.execute(
            "UPDATE khoi_phuc_mat_khau SET da_su_dung = 1 WHERE email = ?", (email,)
        )
        conn.commit()

        print(f"[AUTH] ✅ Password reset for: {email}")
        return {"success": True, "message": "Đặt lại mật khẩu thành công!"}

    finally:
        conn.close()
