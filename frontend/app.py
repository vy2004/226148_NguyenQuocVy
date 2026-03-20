import streamlit as st
import streamlit.components.v1 as components
import sys
import os
import time

# Cấu hình path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Kết nối backend
from backend.rag_chain_pg import (
    ask_pg, clear_history_pg, get_database_info,
    process_uploaded_pdf, summarize_pdf_text,
)
from backend.db import (
    init_db, save_conversation, save_message,
    load_all_conversations, delete_conversation,
    update_conversation_title, save_phan_hoi,
    save_message_sources,
)
from backend.auth import (
    register_user, login_user,
    create_reset_token, reset_password,
    is_admin,
)
from backend.email_service import send_reset_email
from backend.admin_services import (
    list_users,
    update_user_role,
    lock_user,
    unlock_user,
    list_conversations as admin_list_conversations,
    list_feedback as admin_list_feedback,
    update_feedback_status,
    list_system_docs,
    create_system_doc,
    delete_system_doc,
    reindex_all,
    get_rag_stats,
)

# ============================================================
# CẤU HÌNH TRANG
# ============================================================
st.set_page_config(
    page_title="Lịch Sử Việt Nam AI",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS — CORTEX-STYLE LAYOUT + AUTH PAGES
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ===== RESET ===== */
    #MainMenu, footer, header,
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    .stDeployButton {
        display: none !important;
        visibility: hidden !important;
    }
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important; }

    /* ===== NỀN TRẮNG ===== */
    .stApp { background: #f9f9f9 !important; }
    .stMain { background: #f9f9f9 !important; }

    /* ===== AUTH PAGE STYLES ===== */
    .auth-container {
        max-width: 420px;
        margin: 0 auto;
        padding: 40px 0;
    }
    .auth-card {
        background: white;
        border-radius: 20px;
        padding: 40px 36px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06);
        border: 1px solid #f0f0f0;
    }
    .auth-logo {
        text-align: center;
        margin-bottom: 28px;
    }
    .auth-orb {
        width: 70px; height: 70px;
        background: radial-gradient(circle at 40% 40%, #e8ddff, #c4b5fd 40%, #a78bfa 70%, #8b5cf6);
        border-radius: 50%;
        margin: 0 auto 16px auto;
        box-shadow: 0 8px 32px rgba(139, 92, 246, 0.25);
    }
    .auth-title {
        font-size: 24px;
        font-weight: 700;
        color: #000000 !important;
        text-align: center;
        margin-bottom: 4px;
    }
    .auth-subtitle {
        font-size: 14px;
        color: #555555 !important;
        text-align: center;
        margin-bottom: 24px;
    }
    .auth-footer {
        text-align: center;
        margin-top: 20px;
        font-size: 11px;
        color: #888888 !important;
    }

    /* Auth form inputs — white background, black text */
    .auth-container .stTextInput > div > div > input,
    .auth-container input[type="text"],
    .auth-container input[type="password"] {
        background: #ffffff !important;
        color: #000000 !important;
        border: 1.5px solid #d0d0d0 !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
    }
    .auth-container .stTextInput > div > div > input:focus,
    .auth-container input:focus {
        border-color: #7c3aed !important;
        box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important;
    }
    .auth-container .stTextInput > div > div > input::placeholder,
    .auth-container input::placeholder {
        color: #999999 !important;
    }

    /* Auth form labels — black text */
    .auth-container .stTextInput > label,
    .auth-container label {
        color: #000000 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        margin-bottom: 4px !important;
    }

    /* Auth all text black */
    .auth-container, .auth-container * {
        color: #000000 !important;
    }
    .auth-container .auth-subtitle {
        color: #555555 !important;
    }
    .auth-container .auth-footer {
        color: #888888 !important;
    }

    /* Auth primary buttons — purple */
    .auth-container .stFormSubmitButton > button,
    .auth-container .stFormSubmitButton > button:active,
    .auth-container .stFormSubmitButton > button:focus,
    .auth-container button[kind="primary"],
    .auth-container button[type="submit"],
    .stApp .auth-container .stFormSubmitButton > button {
        background: linear-gradient(135deg, #7c3aed, #a78bfa) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        padding: 12px 20px !important;
        width: 100% !important;
        transition: opacity 0.2s !important;
    }
    .auth-container .stFormSubmitButton > button:hover,
    .auth-container button[kind="primary"]:hover,
    .stApp .auth-container .stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #6d28d9, #8b5cf6) !important;
        opacity: 0.95 !important;
    }

    /* Auth secondary buttons — purple outline */
    .auth-container .stButton > button {
        background: #ffffff !important;
        color: #7c3aed !important;
        border: 1.5px solid #7c3aed !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        padding: 10px 16px !important;
        min-height: auto !important;
        transition: all 0.2s !important;
    }
    .auth-container .stButton > button:hover {
        border-color: #6d28d9 !important;
        color: #ffffff !important;
        background: #7c3aed !important;
    }

    /* Auth form container — white card */
    .auth-container [data-testid="stForm"] {
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
    }

    /* Auth alerts */
    .auth-container .stAlert {
        border-radius: 10px !important;
        font-size: 13px !important;
    }

    /* ===== SIDEBAR ===== */
    section[data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #f0f0f0 !important;
        min-width: 240px !important;
        max-width: 240px !important;
    }
    section[data-testid="stSidebar"] .block-container,
    section[data-testid="stSidebar"] > div {
        padding-top: 12px !important;
    }

    /* Toggle buttons */
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarExpandButton"],
    [data-testid="collapsedControl"] button {
        color: #888 !important; background: transparent !important; border: none !important;
    }
    button[data-testid="stSidebarCollapseButton"]:hover,
    button[data-testid="stSidebarExpandButton"]:hover,
    [data-testid="collapsedControl"] button:hover {
        color: #333 !important; background: #f5f5f5 !important; border-radius: 8px !important;
    }
    [data-testid="collapsedControl"] { background: transparent !important; }

    /* Sidebar labels */
    .sb-section-title {
        font-size: 11px;
        color: #aaaaaa;
        font-weight: 600;
        padding: 14px 0 4px 0;
        letter-spacing: 0.5px;
    }

    /* Sidebar nav items */
    .sb-nav {
        display: flex; align-items: center; gap: 10px;
        padding: 8px 12px; border-radius: 10px;
        color: #444; font-size: 14px; font-weight: 400;
        cursor: pointer; transition: background 0.15s;
        text-decoration: none; margin-bottom: 2px;
    }
    .sb-nav:hover { background: #f5f5f5; }
    .sb-nav-icon { font-size: 16px; color: #888; width: 20px; text-align: center; }

    /* Sidebar buttons */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important; border: none !important;
        border-radius: 10px !important; color: #444444 !important;
        font-size: 13px !important; font-weight: 400 !important;
        padding: 8px 12px !important; text-align: left !important;
        justify-content: flex-start !important; width: 100% !important;
        white-space: nowrap !important; overflow: hidden !important;
        text-overflow: ellipsis !important; transition: all 0.15s ease !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #f5f5f5 !important; color: #222 !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: #f3f0ff !important; color: #7c3aed !important; font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #f0f0f0 !important; margin: 6px 0 !important;
    }

    /* New chat button — purple */
    .new-chat-btn > button {
        background: #7c3aed !important; color: #ffffff !important;
        border: none !important; border-radius: 12px !important;
        font-weight: 500 !important; font-size: 14px !important;
        padding: 10px 16px !important;
    }
    .new-chat-btn > button:hover {
        background: #6d28d9 !important; color: #ffffff !important;
    }

    /* File uploader */
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: #fafafa !important; border: 1px dashed #ddd !important; border-radius: 10px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #7c3aed !important; background: #faf5ff !important;
    }

    /* ===== MAIN CONTENT — CENTERED ===== */
    .main .block-container,
    .stAppViewBlockContainer {
        max-width: 720px !important;
        padding: 0 20px 20px 20px !important;
        margin: 0 auto !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: calc(100vh - 40px) !important;
    }

    /* ===== WELCOME — CENTERED ===== */
    .welcome-center {
        text-align: center;
        padding-top: 20px;
        padding-bottom: 8px;
        width: 100%;
    }
    .welcome-orb {
        width: 90px; height: 90px;
        background: radial-gradient(circle at 40% 40%, #e8ddff, #c4b5fd 40%, #a78bfa 70%, #8b5cf6);
        border-radius: 50%;
        margin: 0 auto 24px auto;
        box-shadow: 0 8px 32px rgba(139, 92, 246, 0.25);
        opacity: 0.9;
    }
    .welcome-hello {
        font-size: 32px !important;
        font-weight: 400 !important;
        color: #a78bfa !important;
        margin-bottom: 4px !important;
        line-height: 1.2 !important;
    }
    .welcome-question {
        font-size: 32px !important;
        font-weight: 700 !important;
        color: #1a1a1a !important;
        margin-bottom: 24px !important;
        line-height: 1.2 !important;
    }

    /* Force Streamlit markdown override */
    .stMarkdown .welcome-hello { font-size: 32px !important; color: #a78bfa !important; font-weight: 400 !important; }
    .stMarkdown .welcome-question { font-size: 32px !important; color: #1a1a1a !important; font-weight: 700 !important; }

    /* ===== CHAT INPUT — CENTERED CARD ===== */
    div[data-testid="stChatInput"] {
        max-width: 620px !important;
        margin: 0 auto !important;
        width: 100% !important;
    }
    div[data-testid="stChatInput"] textarea {
        background: #ffffff !important;
        border: 1px solid #e5e5e5 !important;
        border-radius: 16px !important;
        color: #1a1a1a !important;
        font-size: 15px !important;
        padding: 16px 50px 16px 20px !important;
        min-height: 50px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder { color: #b0b0b0 !important; }
    div[data-testid="stChatInput"] textarea:focus {
        border-color: #a78bfa !important;
        box-shadow: 0 0 0 3px rgba(167,139,250,0.1) !important;
    }

    /* Send button */
    div[data-testid="stChatInput"] button {
        background: linear-gradient(135deg, #7c3aed, #a78bfa) !important;
        color: #fff !important; border-radius: 50% !important;
        width: 34px !important; height: 34px !important;
        position: absolute !important;
        right: 8px !important; bottom: 12px !important;
        top: auto !important; transform: none !important;
    }
    div[data-testid="stChatInput"] button:hover { opacity: 0.85 !important; }

    /* Bottom area */
    div[data-testid="stBottom"] { background: #f9f9f9 !important; border-top: none !important; }
    div[data-testid="stBottom"] > div { background: #f9f9f9 !important; }
    div[data-testid="stBottomBlockContainer"] {
        max-width: 720px !important;
        margin: 0 auto !important;
        padding: 8px 20px 16px 20px !important;
        background: #f9f9f9 !important;
    }
    .stBottom, .stBottom > div, .stBottom iframe { background: #f9f9f9 !important; }

    /* ===== INPUT BOTTOM BAR (attach, prompts) ===== */
    .input-bar {
        display: flex; align-items: center; justify-content: space-between;
        max-width: 620px; margin: 8px auto 0 auto; width: 100%;
        padding: 0 4px;
    }
    .input-bar-left {
        display: flex; align-items: center; gap: 6px;
    }
    .input-bar-right {
        display: flex; align-items: center; gap: 6px;
    }
    .bar-chip {
        display: inline-flex; align-items: center; gap: 5px;
        font-size: 12px; color: #888; padding: 4px 10px;
        border-radius: 8px; cursor: pointer; transition: all 0.15s;
    }
    .bar-chip:hover { background: #f0f0f0; color: #555; }
    .bar-chip-purple {
        color: #7c3aed; border: 1px solid #e0d4ff;
        background: #faf5ff; border-radius: 20px;
        padding: 5px 14px; font-weight: 500;
    }
    .bar-chip-purple:hover { background: #f0e8ff; }

    /* ===== SUGGESTION CARDS — CENTERED ===== */
    .cards-section-title {
        display: flex; align-items: center; gap: 6px;
        font-size: 13px; color: #888; margin: 20px 0 12px 0;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 12px !important;
        justify-content: center !important;
    }

    .main .stButton > button {
        background: #ffffff !important;
        border: 1px solid #eeeeee !important;
        border-radius: 14px !important;
        color: #444 !important;
        font-size: 12px !important;
        font-weight: 400 !important;
        padding: 16px 14px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        min-height: 90px !important;
        line-height: 1.5 !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
    }
    .main .stButton > button:hover {
        background: #fafafa !important;
        border-color: #ddd !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
    }

    /* ===== CHAT MESSAGES ===== */
    div[data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 12px 0 !important;
        max-width: 100% !important;
    }
    div[data-testid="stChatMessage"] .stMarkdown p {
        color: #1a1a1a !important;
        font-size: 15px !important;
        line-height: 1.7 !important;
    }
    div[data-testid="stChatMessage"] [data-testid="stAvatar"],
    div[data-testid="stChatMessage"] .stAvatar {
        width: 32px !important; height: 32px !important; border-radius: 50% !important;
    }

    /* ===== EXPANDER ===== */
    div[data-testid="stExpander"] {
        background: #fafafa !important; border: 1px solid #eee !important;
        border-radius: 12px !important; margin-top: 8px !important;
    }
    div[data-testid="stExpander"] summary { color: #666 !important; font-size: 13px !important; }

    /* Source chips */
    .src-chip {
        display: inline-block; background: #f3f0ff; color: #7c3aed;
        font-size: 12px; font-weight: 500; padding: 5px 12px;
        border-radius: 16px; margin: 3px 4px 3px 0; border: 1px solid #e9e5f5;
    }
    .confidence-badge {
        display: inline-block; font-size: 11px; font-weight: 600;
        padding: 3px 12px; border-radius: 16px; margin-top: 6px;
    }
    .confidence-high { background: #ecfdf5; color: #059669; border: 1px solid #d1fae5; }
    .confidence-medium { background: #fffbeb; color: #d97706; border: 1px solid #fef3c7; }
    .confidence-low { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

    .upload-success {
        background: #ecfdf5; border: 1px solid #d1fae5; border-radius: 10px;
        padding: 8px 12px; color: #059669; font-size: 12px; margin: 6px 0;
    }

    .stSpinner > div > div { border-top-color: #7c3aed !important; }

    /* ===== FEEDBACK BUTTONS (like/dislike) ===== */
    div[data-testid="stChatMessage"] .feedback-wrap .stButton > button {
        background: transparent !important;
        border: 1px solid #e5e5e5 !important;
        border-radius: 8px !important;
        padding: 2px 10px !important;
        font-size: 16px !important;
        min-height: 32px !important;
        max-height: 32px !important;
        line-height: 1 !important;
        color: #888 !important;
        box-shadow: none !important;
        transition: all 0.15s !important;
    }
    div[data-testid="stChatMessage"] .feedback-wrap .stButton > button:hover {
        background: #f5f5f5 !important;
        border-color: #ccc !important;
        color: #555 !important;
    }
    .feedback-done {
        display: inline-flex; align-items: center; gap: 4px;
        font-size: 12px; color: #888; padding: 4px 0;
    }
    .feedback-done-like { color: #059669; }
    .feedback-done-dislike { color: #dc2626; }

    div[data-testid="stChatMessage"] .feedback-form textarea {
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 10px !important;
        font-size: 13px !important;
        color: #1a1a1a !important;
        min-height: 60px !important;
        max-height: 120px !important;
    }
    div[data-testid="stChatMessage"] .feedback-form .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #a78bfa) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 6px 16px !important;
        min-height: 34px !important;
        max-height: 34px !important;
    }
    div[data-testid="stChatMessage"] .feedback-form .stButton > button:hover {
        opacity: 0.9 !important;
    }

    /* Markdown in chat */
    div[data-testid="stChatMessage"] .stMarkdown h1,
    div[data-testid="stChatMessage"] .stMarkdown h2,
    div[data-testid="stChatMessage"] .stMarkdown h3 { color: #1a1a1a !important; }
    div[data-testid="stChatMessage"] .stMarkdown li { color: #3c4043 !important; }
    div[data-testid="stChatMessage"] .stMarkdown strong { color: #1a1a1a !important; }

    /* User info at bottom of sidebar */
    .sb-user {
        display: flex; align-items: center; gap: 10px;
        padding: 10px 12px; border-top: 1px solid #f0f0f0;
        margin-top: 12px;
    }
    .sb-user-avatar {
        width: 34px; height: 34px; border-radius: 50%;
        background: linear-gradient(135deg, #7c3aed, #a78bfa);
        color: white; display: flex; align-items: center; justify-content: center;
        font-size: 14px; font-weight: 600;
    }
    .sb-user-info { font-size: 12px; color: #888; line-height: 1.4; }
    .sb-user-name { color: #333; font-weight: 500; font-size: 13px; }

    /* Logout button */
    .logout-btn > button {
        background: transparent !important;
        color: #dc2626 !important;
        border: 1px solid #fecaca !important;
        border-radius: 10px !important;
        font-size: 12px !important;
        padding: 6px 12px !important;
    }
    .logout-btn > button:hover {
        background: #fef2f2 !important;
    }
</style>
""", unsafe_allow_html=True)

# JavaScript để thay thế text tiếng Anh trong file uploader
components.html("""
<script>
function translateFileUploader() {
    const doc = window.parent.document;

    // Tìm tất cả span trong file uploader
    const spans = doc.querySelectorAll('section[aria-label] span');
    spans.forEach(function(span) {
        if (span.textContent.indexOf('Drag') !== -1) {
            span.textContent = 'Kéo và thả tệp vào đây';
        }
    });

    // Tìm tất cả small trong file uploader
    const smalls = doc.querySelectorAll('section[aria-label] small');
    smalls.forEach(function(small) {
        if (small.textContent.indexOf('Limit') !== -1) {
            small.textContent = 'Giới hạn 200MB mỗi tệp • PDF';
        }
    });

    // Tìm nút Browse files
    const buttons = doc.querySelectorAll('section[aria-label] button');
    buttons.forEach(function(btn) {
        if (btn.textContent.indexOf('Browse') !== -1) {
            btn.textContent = 'Chọn tệp';
        }
    });
}

// Chạy nhiều lần để đảm bảo
setTimeout(translateFileUploader, 500);
setTimeout(translateFileUploader, 1500);
setTimeout(translateFileUploader, 3000);
var observer = new MutationObserver(function() {
    setTimeout(translateFileUploader, 100);
});
observer.observe(window.parent.document.body, { childList: true, subtree: true });
</script>
""", height=0)

# ============================================================
# KHỞI TẠO DATABASE + SESSION STATE
# ============================================================
init_db()

if "user" not in st.session_state:
    st.session_state.user = None
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"  # login, register, forgot, reset
if "reset_email" not in st.session_state:
    st.session_state.reset_email = None
if "reset_delivery" not in st.session_state:
    st.session_state.reset_delivery = None

# ============================================================
# AUTH PAGES — ĐĂNG NHẬP / ĐĂNG KÝ / QUÊN MẬT KHẨU
# ============================================================
def show_login_page():
    """Trang đăng nhập."""
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown("""
    <div class="auth-logo">
        <div class="auth-orb"></div>
        <div class="auth-title">Đăng nhập</div>
        <div class="auth-subtitle">Chatbot Lịch Sử Việt Nam</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("📧 Email", placeholder="Nhập email của bạn")
        password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
        submit = st.form_submit_button("Đăng nhập", use_container_width=True, type="primary")

        if submit:
            if not email or not password:
                st.error("Vui lòng nhập đầy đủ email và mật khẩu")
            else:
                result = login_user(email, password)
                if result["success"]:
                    st.session_state.user = result["user"]
                    st.session_state.conversations = load_all_conversations(
                        ma_nguoi_dung=result["user"]["id"]
                    )
                    st.session_state.current_conv_id = None
                    st.success(result["message"])
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(result["message"])

    # Links
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Tạo tài khoản mới", key="goto_register", use_container_width=True):
            st.session_state.auth_page = "register"
            st.rerun()
    with col2:
        if st.button("Quên mật khẩu?", key="goto_forgot", use_container_width=True):
            st.session_state.auth_page = "forgot"
            st.rerun()

    st.markdown("""
    <div class="auth-footer">
        🏛️ Chatbot Lịch Sử Việt Nam — Powered by NguyenQuocVy-a.k.a QvyInTheBest
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def show_register_page():
    """Trang đăng ký."""
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown("""
    <div class="auth-logo">
        <div class="auth-orb"></div>
        <div class="auth-title">Tạo tài khoản</div>
        <div class="auth-subtitle">Đăng ký để bắt đầu trò chuyện</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("register_form"):
        display_name = st.text_input("Tên hiển thị", placeholder="Nhập tên của bạn")
        email = st.text_input("Email", placeholder="Nhập email của bạn")
        password = st.text_input("Mật khẩu", type="password", placeholder="Tối thiểu 6 ký tự")
        confirm_password = st.text_input("Xác nhận mật khẩu", type="password", placeholder="Nhập lại mật khẩu")
        submit = st.form_submit_button("Đăng ký", use_container_width=True, type="primary")

        if submit:
            if not email or not password or not display_name:
                st.error("Vui lòng nhập đầy đủ thông tin")
            elif password != confirm_password:
                st.error("Mật khẩu xác nhận không khớp")
            else:
                result = register_user(email, password, display_name)
                if result["success"]:
                    st.success(result["message"] + " Đang đăng nhập...")
                    st.session_state.user = result["user"]
                    st.session_state.conversations = {}
                    st.session_state.current_conv_id = None
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(result["message"])

    if st.button("⬅️ Quay lại đăng nhập", key="back_to_login_from_register", use_container_width=True):
        st.session_state.auth_page = "login"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def show_forgot_password_page():
    """Trang quên mật khẩu — nhập email."""
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown("""
    <div class="auth-logo">
        <div class="auth-orb"></div>
        <div class="auth-title">Quên mật khẩu</div>
        <div class="auth-subtitle">Nhập email để nhận mã xác nhận</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("forgot_form"):
        email = st.text_input("Email", placeholder="Nhập email đã đăng ký")
        submit = st.form_submit_button("Gửi mã xác nhận", use_container_width=True, type="primary")

        if submit:
            if not email:
                st.error("Vui lòng nhập email")
            else:
                # Tạo mã OTP
                result = create_reset_token(email)
                if result["success"]:
                    # Gửi email
                    email_result = send_reset_email(email, result["token"])
                    if email_result["success"]:
                        st.session_state.reset_email = email
                        st.session_state.reset_delivery = email_result.get("delivery")
                        st.success(email_result["message"])
                        st.session_state.auth_page = "reset"
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(email_result["message"])
                else:
                    st.error(result["message"])

    if st.button("Quay lại đăng nhập", key="back_to_login_from_forgot", use_container_width=True):
        st.session_state.auth_page = "login"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def show_reset_password_page():
    """Trang nhập mã OTP và mật khẩu mới."""
    email = st.session_state.get("reset_email", "")

    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="auth-logo">
        <div class="auth-orb"></div>
        <div class="auth-title">Đặt lại mật khẩu</div>
        <div class="auth-subtitle">Nhập mã OTP đã gửi đến {email}</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("reset_form"):
        otp = st.text_input("Mã OTP (6 chữ số)", placeholder="Nhập mã OTP", max_chars=6)
        new_password = st.text_input("Mật khẩu mới", type="password", placeholder="Tối thiểu 6 ký tự")
        confirm = st.text_input("Xác nhận mật khẩu mới", type="password", placeholder="Nhập lại mật khẩu mới")
        submit = st.form_submit_button("Đặt lại mật khẩu", use_container_width=True, type="primary")

        if submit:
            if not otp or not new_password:
                st.error("Vui lòng nhập đầy đủ thông tin")
            elif new_password != confirm:
                st.error("Mật khẩu xác nhận không khớp")
            else:
                result = reset_password(email, otp, new_password)
                if result["success"]:
                    st.success(result["message"] + " Hãy đăng nhập với mật khẩu mới.")
                    st.session_state.auth_page = "login"
                    st.session_state.reset_email = None
                    st.session_state.reset_delivery = None
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(result["message"])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Gửi lại mã OTP", key="resend_otp", use_container_width=True):
            result = create_reset_token(email)
            if result["success"]:
                email_result = send_reset_email(email, result["token"])
                st.session_state.reset_delivery = email_result.get("delivery")
                if email_result["success"]:
                    st.success(email_result["message"])
                else:
                    st.error(email_result["message"])
    with col2:
        if st.button("Quay lại", key="back_to_forgot", use_container_width=True):
            st.session_state.auth_page = "forgot"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# KIỂM TRA ĐĂNG NHẬP
# ============================================================
if st.session_state.user is None:
    # Chưa đăng nhập → hiển thị trang auth
    page = st.session_state.auth_page
    if page == "login":
        show_login_page()
    elif page == "register":
        show_register_page()
    elif page == "forgot":
        show_forgot_password_page()
    elif page == "reset":
        show_reset_password_page()
    st.stop()

# ============================================================
# ĐÃ ĐĂNG NHẬP — CHATBOT
# ============================================================
user = st.session_state.user

if "conversations" not in st.session_state:
    st.session_state.conversations = load_all_conversations(ma_nguoi_dung=user["id"])
if "current_conv_id" not in st.session_state:
    st.session_state.current_conv_id = None
if "uploaded_pdf_text" not in st.session_state:
    st.session_state.uploaded_pdf_text = None
if "uploaded_pdf_name" not in st.session_state:
    st.session_state.uploaded_pdf_name = None
if "admin_page" not in st.session_state:
    st.session_state.admin_page = "chat"  # chat | admin

def get_current_messages():
    cid = st.session_state.current_conv_id
    if cid and cid in st.session_state.conversations:
        return st.session_state.conversations[cid]["messages"]
    return []

def create_new_conversation():
    conv_id = f"conv_{int(time.time() * 1000)}"
    st.session_state.conversations[conv_id] = {"title": "Cuộc trò chuyện mới", "messages": []}
    st.session_state.current_conv_id = conv_id
    save_conversation(ma_cuoc_tro_chuyen=conv_id, tieu_de="Cuộc trò chuyện mới", ma_nguoi_dung=user["id"])
    clear_history_pg(session_id=conv_id)
    return conv_id

def generate_title(question: str) -> str:
    title = question.strip()
    for prefix in ["hãy ", "cho tôi biết ", "tóm tắt ", "giải thích ", "kể về ", "nói về ", "trình bày "]:
        if title.lower().startswith(prefix):
            title = title[len(prefix):]
            break
    if len(title) > 40:
        title = title[:37] + "..."
    return title.capitalize() if title else "Cuộc trò chuyện mới"


def show_admin_page():
    """Trang quản trị: Quản lý người dùng, Lịch sử hỏi đáp, Phản hồi, Tài liệu hệ thống, Thống kê RAG."""
    st.title("Trang quản trị")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Quản lý người dùng",
        "Lịch sử hỏi đáp",
        "Phản hồi người dùng",
        "Tài liệu hệ thống",
        "Thống kê RAG",
    ])

    with tab1:
        st.subheader("Quản lý người dùng")
        users = list_users()
        if not users:
            st.info("Chưa có người dùng nào.")
        else:
            for u in users:
                ma = u["ma_nguoi_dung"]
                role = u.get("vai_tro") or "user"
                locked = u.get("khoa_tai_khoan", 0)
                col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 2])
                with col1:
                    st.text(f"{u['email']}")
                with col2:
                    st.text(f"{u['ten_hien_thi']} ({role})")
                with col3:
                    new_role = "admin" if role == "user" else "user"
                    if st.button("Đổi vai trò", key=f"role_{ma}"):
                        ok, msg = update_user_role(ma, new_role)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                with col4:
                    if locked:
                        if st.button("Mở khóa", key=f"unlock_{ma}"):
                            unlock_user(ma)
                            st.rerun()
                    else:
                        if ma != user["id"] and st.button("Khóa", key=f"lock_{ma}"):
                            lock_user(ma)
                            st.rerun()
                with col5:
                    if locked:
                        st.caption("🔒 Đã khóa")
                st.markdown("---")

    with tab2:
        st.subheader("Lịch sử hỏi đáp toàn hệ thống")
        from backend.db import load_messages as db_load_messages
        convs = admin_list_conversations()
        if not convs:
            st.info("Chưa có cuộc trò chuyện.")
        else:
            for c in convs:
                with st.expander(f"{c.get('tieu_de', 'N/A')} — {c.get('email', 'N/A')} ({str(c.get('ngay_tao', ''))[:19]})"):
                    st.caption(f"ID: {c['ma_cuoc_tro_chuyen']}")
                    st.text(f"Người dùng: {c.get('ten_hien_thi')} ({c.get('email')})")
                    try:
                        msgs = db_load_messages(c["ma_cuoc_tro_chuyen"])
                        for m in msgs[-10:]:
                            content = (m.get("content") or "")[:200]
                            if len(m.get("content") or "") > 200:
                                content += "..."
                            st.text(f"{m['role']}: {content}")
                    except Exception:
                        pass

    with tab3:
        st.subheader("Phản hồi người dùng")
        feedbacks = admin_list_feedback()
        if not feedbacks:
            st.info("Chưa có phản hồi.")
        else:
            for fb in feedbacks:
                status = fb.get("trang_thai_xu_ly") or "moi"
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"Loại: {fb.get('loai')} | Trạng thái: {status}")
                    st.caption(fb.get("noi_dung_phan_hoi") or "(không có nội dung)")
                    st.caption(f"Tin nhắn: {(fb.get('noi_dung_tin_nhan') or '')[:150]}...")
                with col2:
                    new_status = st.selectbox(
                        "Xử lý",
                        ["moi", "daxem", "dong"],
                        index=["moi", "daxem", "dong"].index(status) if status in ["moi", "daxem", "dong"] else 0,
                        key=f"fb_st_{fb['ma_phan_hoi']}",
                    )
                    if new_status != status and st.button("Cập nhật", key=f"fb_btn_{fb['ma_phan_hoi']}"):
                        ok, msg = update_feedback_status(fb["ma_phan_hoi"], new_status)
                        if ok:
                            st.rerun()
                st.markdown("---")

    with tab4:
        st.subheader("Tài liệu hệ thống (RAG)")
        docs = list_system_docs()
        if not docs:
            st.info("Chưa có tài liệu hệ thống. Thêm file PDF vào kho dữ liệu runtime hoặc tải lên bên dưới.")
        else:
            for d in docs:
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.text(f"{d.get('ten_file')} — {d.get('duong_dan', '')}")
                with c2:
                    if st.button("Xóa", key=f"del_doc_{d.get('ma_tai_lieu')}"):
                        ok, msg = delete_system_doc(d["ma_tai_lieu"])
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                st.markdown("---")
        st.markdown("**Thêm tài liệu** (sẽ lưu vào kho dữ liệu runtime)")
        uploaded = st.file_uploader("Chọn PDF", type=["pdf"], key="admin_pdf_upload")
        if uploaded:
            if st.button("Lưu tài liệu hệ thống"):
                ok, msg = create_system_doc(uploaded, uploaded.name)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with tab5:
        st.subheader("Thống kê RAG & Đồng bộ chỉ mục")
        stats = get_rag_stats()
        if stats.get("error"):
            st.warning(stats["error"])
        else:
            st.metric("Tổng số chunks", stats.get("total_chunks", 0))
            st.caption(f"Collection: {stats.get('collection_name')} | Thư mục: {stats.get('persist_dir', '')}")
        st.caption("Nút bên dưới chỉ index tài liệu mới, bỏ qua tài liệu/chunks đã có để chạy nhanh hơn.")
        if st.button("Đồng bộ chỉ mục (chỉ tài liệu mới)", type="primary"):
            with st.spinner("Đang đồng bộ tài liệu mới vào ChromaDB..."):
                ok, msg = reindex_all()
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


# ============================================================
# SIDEBAR — FULL NAVIGATION + HISTORY
# ============================================================
with st.sidebar:
    # Logo
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;padding:4px 0 8px 0;">
        <span style="font-size:16px;font-weight:600;color:#1a1a1a;">Lịch Sử Việt Nam</span>
    </div>
    """, unsafe_allow_html=True)

    # Admin: chuyển Trang chủ / Trang quản trị
    if is_admin(user):
        page_choice = st.radio(
            "Chế độ",
            options=["Trang chủ", "Trang quản trị"],
            index=0 if st.session_state.admin_page == "chat" else 1,
            key="admin_page_radio",
            label_visibility="collapsed",
        )
        new_admin_page = "admin" if page_choice == "Trang quản trị" else "chat"
        if new_admin_page != st.session_state.admin_page:
            st.session_state.admin_page = new_admin_page
            st.rerun()
        st.markdown("---")

    # New chat button (purple)
    st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
    if st.button("Cuộc trò chuyện mới", key="new_chat_btn", use_container_width=True):
        create_new_conversation()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")


    # PDF Upload
    st.markdown('<span class="sb-section-title">Đính kèm tài liệu</span>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Chọn tệp PDF", type=["pdf"], key="pdf_uploader", label_visibility="collapsed")

    if uploaded_file is not None:
        if st.session_state.uploaded_pdf_name != uploaded_file.name:
            with st.spinner("Đang xử lý..."):
                # Truyền user_id vào process_uploaded_pdf
                result = process_uploaded_pdf(uploaded_file, user["id"])
            if result["success"]:
                st.session_state.uploaded_pdf_text = result["text"]
                st.session_state.uploaded_pdf_name = result["filename"]
                if result.get("already_indexed"):
                    st.markdown(f'<div class="upload-success">⏭️ <b>{result["filename"]}</b> — đã được index trước đó, không cần xử lý lại</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="upload-success">✅ <b>{result["filename"]}</b> — {result["chunks_count"]} đoạn</div>', unsafe_allow_html=True)
            else:
                st.error(f"❌ {result.get('error', 'Lỗi')}")
        else:
            st.markdown(f'<div class="upload-success">✅ <b>{uploaded_file.name}</b> sẵn sàng</div>', unsafe_allow_html=True)

        if st.button("📝 Tóm tắt tài liệu", key="summarize_pdf_btn", use_container_width=True):
            st.session_state["pending_summarize"] = True
            st.rerun()

    st.markdown("---")

    # Conversation history
    if st.session_state.conversations:
        st.markdown('<span class="sb-section-title">💬 Hội thoại gần đây</span>', unsafe_allow_html=True)

        sorted_convs = sorted(st.session_state.conversations.items(), key=lambda x: x[0], reverse=True)

        for conv_id, conv_data in sorted_convs:
            title = conv_data.get("title", "Cuộc trò chuyện mới")
            is_active = (conv_id == st.session_state.current_conv_id)
            btn_type = "primary" if is_active else "secondary"

            c1, c2 = st.columns([5, 1])
            with c1:
                if st.button(f"{title}", key=f"sb_{conv_id}", use_container_width=True, type=btn_type):
                    st.session_state.current_conv_id = conv_id
                    st.rerun()
            with c2:
                if st.button("🗑️", key=f"del_{conv_id}"):
                    delete_conversation(conv_id)
                    del st.session_state.conversations[conv_id]
                    if st.session_state.current_conv_id == conv_id:
                        st.session_state.current_conv_id = None
                    clear_history_pg(session_id=conv_id)
                    st.rerun()

    st.markdown("---")

    # User info at bottom — hiển thị thông tin thật
    avatar_letter = user["display_name"][0].upper() if user["display_name"] else "U"
    st.markdown(f"""
    <div class="sb-user">
        <div class="sb-user-avatar">{avatar_letter}</div>
        <div>
            <div class="sb-user-name">{user["display_name"]}</div>
            <div class="sb-user-info">{user["email"]}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Logout button
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("🚪 Đăng xuất", key="logout_btn", use_container_width=True):
        for key in ["user", "conversations", "current_conv_id", "uploaded_pdf_text", "uploaded_pdf_name"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.auth_page = "login"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# NỘI DUNG CHÍNH — CĂN GIỮA (hoặc Trang quản trị)
# ============================================================
if st.session_state.get("admin_page") == "admin" and is_admin(user):
    show_admin_page()
    st.stop()

current_messages = get_current_messages()

if not current_messages:
    # Orb + Greeting
    display_name = user["display_name"]
    st.markdown(f"""
    <div class="welcome-center">
        <div class="welcome-orb"></div>
        <div class="welcome-hello">Xin chào, {display_name}</div>
        <div class="welcome-question">Hôm nay tôi có thể giúp gì?</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# HIỂN THỊ LỊCH SỬ CHAT
# ============================================================
for idx, msg in enumerate(current_messages):
    avatar = "👤" if msg["role"] == "user" else "🏛️"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

        if msg["role"] == "assistant":
            ma_tin_nhan = msg.get("ma_tin_nhan")
            feedback_state = st.session_state.get(f"fb_done_{ma_tin_nhan}")

            if feedback_state == "thich":
                st.markdown('<span class="feedback-done feedback-done-like">👍 Cảm ơn phản hồi của bạn</span>', unsafe_allow_html=True)
            elif feedback_state == "khong_thich":
                st.markdown('<span class="feedback-done feedback-done-dislike">👎 Cảm ơn phản hồi của bạn</span>', unsafe_allow_html=True)
            elif ma_tin_nhan:
                st.markdown('<div class="feedback-wrap">', unsafe_allow_html=True)
                col_like, col_dislike, col_pad = st.columns([1, 1, 10])
                with col_like:
                    if st.button("👍", key=f"like_{ma_tin_nhan}"):
                        save_phan_hoi(ma_tin_nhan, "thich", ma_nguoi_dung=user["id"])
                        st.session_state[f"fb_done_{ma_tin_nhan}"] = "thich"
                        st.rerun()
                with col_dislike:
                    if st.button("👎", key=f"dislike_{ma_tin_nhan}"):
                        st.session_state[f"fb_open_{ma_tin_nhan}"] = True
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                if st.session_state.get(f"fb_open_{ma_tin_nhan}"):
                    st.markdown('<div class="feedback-form">', unsafe_allow_html=True)
                    fb_text = st.text_area(
                        "Cho chúng tôi biết vấn đề:",
                        key=f"fb_text_{ma_tin_nhan}",
                        placeholder="Câu trả lời không chính xác, thiếu thông tin, ...",
                        max_chars=500,
                    )
                    fc1, fc2, _ = st.columns([2, 2, 8])
                    with fc1:
                        if st.button("Gửi phản hồi", key=f"fb_submit_{ma_tin_nhan}"):
                            save_phan_hoi(ma_tin_nhan, "khong_thich",
                                          ma_nguoi_dung=user["id"],
                                          noi_dung_phan_hoi=fb_text or "")
                            st.session_state[f"fb_done_{ma_tin_nhan}"] = "khong_thich"
                            st.session_state.pop(f"fb_open_{ma_tin_nhan}", None)
                            st.rerun()
                    with fc2:
                        if st.button("Hủy", key=f"fb_cancel_{ma_tin_nhan}"):
                            st.session_state.pop(f"fb_open_{ma_tin_nhan}", None)
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# SUGGESTION CARDS (chỉ hiện khi chưa có tin nhắn)
# ============================================================
if not current_messages:
    st.markdown('<div class="cards-section-title">✨ Gợi ý phổ biến &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 📎 Đính kèm tệp</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Tổng hợp dữ liệu\n\nTóm tắt sự kiện lịch sử\nBạch Đằng năm 938", use_container_width=True, key="sug1"):
            st.session_state["pending_question"] = "Trận Bạch Đằng năm 938 diễn ra thế nào?"
    with col2:
        if st.button("Phân tích sự kiện\n\nDiễn biến chiến dịch\nĐiện Biên Phủ 1954", use_container_width=True, key="sug2"):
            st.session_state["pending_question"] = "Tóm tắt chiến dịch Điện Biên Phủ 1954"
    with col3:
        if st.button("Kiểm chứng sự kiện\n\nÝ nghĩa Cách mạng\nTháng Tám 1945", use_container_width=True, key="sug3"):
            st.session_state["pending_question"] = "Cách mạng Tháng Tám 1945 có ý nghĩa gì?"

# ============================================================
# XỬ LÝ CÂU HỎI
# ============================================================
def process_question(question: str):
    if not st.session_state.current_conv_id or st.session_state.current_conv_id not in st.session_state.conversations:
        create_new_conversation()
    conv_id = st.session_state.current_conv_id
    conv = st.session_state.conversations[conv_id]
    
    # Kiểm tra xem người dùng có đang yêu cầu tóm tắt tài liệu vừa tải lên không
    q_lower = question.lower()
    pdf_text = st.session_state.get("uploaded_pdf_text", "")
    pdf_name = st.session_state.get("uploaded_pdf_name", "")
    
    is_summary = any(k in q_lower for k in ["tóm tắt", "tom tat"])
    refers_to_doc = any(k in q_lower for k in ["tài liệu", "file", "văn bản", "đoạn", "này", "đó", "bài"])
    
    # Ghi nhận câu hỏi của người dùng
    conv["messages"].append({"role": "user", "content": question})
    save_message(conv_id, "user", question)
    
    if len([m for m in conv["messages"] if m["role"] == "user"]) == 1:
        title = generate_title(question)
        conv["title"] = title
        update_conversation_title(conv_id, title)

    # Chuyển hướng xử lý nếu là câu lệnh tóm tắt tài liệu
    if is_summary and refers_to_doc and pdf_text and len(q_lower.split()) < 15:
        with st.spinner(f"Đang tóm tắt tài liệu {pdf_name}..."):
            response = summarize_pdf_text(pdf_text, pdf_name, session_id=conv_id)
    else:
        # Nếu không phải lệnh tóm tắt, ghép thêm tên tài liệu vào context ẩn để RAG tìm kiếm tốt hơn
        if pdf_name and refers_to_doc:
            # Gửi query ngầm nhắc tên tài liệu nhưng k hiển thị cho người dùng
            search_query = f"{pdf_name} {question}"
        else:
            search_query = question
            
        with st.spinner("Đang suy nghĩ..."):
            response = ask_pg(search_query, session_id=conv_id)
            
    # Xử lý kết quả trả về
    msg_data = {"role": "assistant", "content": response["answer"]}
    sources = response.get("sources", [])
    evaluation = response.get("evaluation", {})
    if sources: msg_data["sources"] = sources
    if evaluation: msg_data["evaluation"] = evaluation
    ma_tin_nhan = save_message(conv_id, "assistant", response["answer"], sources, evaluation)
    if sources:
        save_message_sources(ma_tin_nhan, sources)
    msg_data["ma_tin_nhan"] = ma_tin_nhan
    conv["messages"].append(msg_data)

def process_pdf_summary():
    pdf_text = st.session_state.get("uploaded_pdf_text", "")
    pdf_name = st.session_state.get("uploaded_pdf_name", "tài liệu.pdf")
    if not pdf_text: return
    if not st.session_state.current_conv_id or st.session_state.current_conv_id not in st.session_state.conversations:
        create_new_conversation()
    conv_id = st.session_state.current_conv_id
    conv = st.session_state.conversations[conv_id]
    user_msg = f"Tóm tắt nội dung tệp: {pdf_name}"
    conv["messages"].append({"role": "user", "content": user_msg})
    save_message(conv_id, "user", user_msg)
    if len([m for m in conv["messages"] if m["role"] == "user"]) == 1:
        title = f"Tóm tắt: {pdf_name[:30]}"
        conv["title"] = title
        update_conversation_title(conv_id, title)
    with st.spinner("Đang tóm tắt tài liệu..."):
        response = summarize_pdf_text(pdf_text, pdf_name, session_id=conv_id)
    msg_data = {"role": "assistant", "content": response["answer"]}
    sources = response.get("sources", [])
    evaluation = response.get("evaluation", {})
    if sources: msg_data["sources"] = sources
    if evaluation: msg_data["evaluation"] = evaluation
    ma_tin_nhan = save_message(conv_id, "assistant", response["answer"], sources, evaluation)
    if sources:
        save_message_sources(ma_tin_nhan, sources)
    msg_data["ma_tin_nhan"] = ma_tin_nhan
    conv["messages"].append(msg_data)

# Process events
if st.session_state.get("pending_summarize"):
    del st.session_state["pending_summarize"]
    process_pdf_summary()
    st.rerun()

if "pending_question" in st.session_state:
    q = st.session_state.pop("pending_question")
    process_question(q)
    st.rerun()

if prompt := st.chat_input("Hỏi bất cứ điều gì bạn muốn...."):
    process_question(prompt)
    st.rerun()
