"""
Module email_service: Gửi email reset password qua Resend API (HTTPS).

Biến môi trường cần có:
- RESEND_API_KEY
- RESEND_FROM_EMAIL (ví dụ onboarding@resend.dev hoặc email domain đã verify)
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "").strip()
RESEND_API_URL = "https://api.resend.com/emails"


def _build_html_body(to_email: str, otp_code: str) -> str:
    return f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 500px; margin: 0 auto;
                padding: 30px; background: #f9f9f9; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="width: 60px; height: 60px; background: linear-gradient(135deg, #7c3aed, #a78bfa);
                        border-radius: 50%; margin: 0 auto 16px; display: flex; align-items: center;
                        justify-content: center; font-size: 28px; color: white; line-height: 60px;">🏛️</div>
            <h2 style="color: #1a1a1a; margin: 0;">Đặt lại mật khẩu</h2>
        </div>
        <div style="background: white; padding: 24px; border-radius: 10px; border: 1px solid #eee;">
            <p style="color: #444; font-size: 14px; line-height: 1.6;">
                Bạn đã yêu cầu đặt lại mật khẩu cho tài khoản <strong>{to_email}</strong>.
            </p>
            <p style="color: #444; font-size: 14px;">Mã xác nhận của bạn là:</p>
            <div style="background: #f3f0ff; padding: 16px; border-radius: 10px;
                        text-align: center; margin: 16px 0;">
                <span style="font-size: 32px; font-weight: 700; color: #7c3aed;
                             letter-spacing: 8px;">{otp_code}</span>
            </div>
            <p style="color: #888; font-size: 12px;">
                ⏰ Mã này sẽ hết hạn sau <strong>15 phút</strong>.<br>
                Nếu bạn không yêu cầu, hãy bỏ qua email này.
            </p>
        </div>
        <p style="text-align: center; color: #aaa; font-size: 11px; margin-top: 20px;">
            Chatbot Lịch Sử Việt Nam — AI Assistant
        </p>
    </div>
    """


def _try_send_resend(to_email: str, otp_code: str) -> tuple[bool, str]:
    """Thử gửi mail bằng Resend API. Trả về (success, error_message)."""
    if not RESEND_API_KEY:
        return False, "Thiếu RESEND_API_KEY"
    if not RESEND_FROM_EMAIL:
        return False, "Thiếu RESEND_FROM_EMAIL"

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": "Dat lai mat khau - Chatbot Lich Su Viet Nam",
        "html": _build_html_body(to_email, otp_code),
    }
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(RESEND_API_URL, headers=headers, json=payload, timeout=20)
        if 200 <= response.status_code < 300:
            print(f"[EMAIL] Sent OTP via Resend to: {to_email}")
            return True, ""

        reason = response.text[:400]
        print(f"[EMAIL] Resend failed ({response.status_code}): {reason}")
        return False, f"Resend error {response.status_code}: {reason}"
    except Exception as e:
        print(f"[EMAIL] Resend request failed: {e}")
        return False, str(e)


def send_reset_email(to_email: str, otp_code: str) -> dict:
    """
    Gửi email chứa mã OTP reset password.
    Chỉ trả về success=True khi email gửi thành công.
    """
    sent, error_reason = _try_send_resend(to_email, otp_code)
    if sent:
        return {
            "success": True,
            "message": f"Đã gửi mã OTP đến **{to_email}**. Kiểm tra hộp thư!",
            "delivery": "email",
        }

    return {
        "success": False,
        "message": (
            "Khong the gui email dat lai mat khau. "
            f"Chi tiet: {error_reason}. "
            "Kiem tra lai RESEND_API_KEY va RESEND_FROM_EMAIL tren Hugging Face."
        ),
        "delivery": "failed",
    }
