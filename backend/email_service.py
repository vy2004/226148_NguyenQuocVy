"""
Module email_service: Gửi email reset password qua Gmail SMTP.
Cấu hình trong .env: SMTP_EMAIL, SMTP_PASSWORD (App Password)
Nếu không gửi được email, hiển thị OTP trực tiếp cho người dùng.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def _try_send_smtp(to_email: str, otp_code: str) -> bool:
    """Thử gửi email qua SMTP. Trả về True nếu thành công."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False

    subject = "🔑 Đặt lại mật khẩu - Chatbot Lịch Sử Việt Nam"
    html_body = f"""
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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Chatbot Lịch Sử VN <{SMTP_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        print(f"[EMAIL] ✅ Đã gửi email OTP đến: {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] ⚠️ Không gửi được email: {e}")
        return False


def send_reset_email(to_email: str, otp_code: str) -> dict:
    """
    Gửi email chứa mã OTP reset password.
    Nếu không gửi được, trả về OTP trực tiếp để hiển thị trên UI.
    Returns: {"success": True/False, "message": str, "show_otp": bool, "otp": str or None}
    """
    # Thử gửi email qua SMTP
    if _try_send_smtp(to_email, otp_code):
        return {
            "success": True,
            "message": f"✅ Đã gửi mã OTP đến **{to_email}**. Kiểm tra hộp thư!",
            "show_otp": False,
            "otp": None,
        }

    # Fallback: hiển thị OTP trên giao diện
    print(f"[EMAIL] 📱 Hiển thị OTP trực tiếp cho: {to_email}")
    return {
        "success": True,
        "message": "Mã OTP đã được tạo",
        "show_otp": True,
        "otp": otp_code,
    }
