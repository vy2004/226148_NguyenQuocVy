import streamlit as st
import streamlit.components.v1 as components
import sys
import os
import time

# Cấu hình path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Kết nối backend
from backend.rag_chain_pg import ask_pg, clear_history_pg, get_database_info

# ============================================================
# CẤU HÌNH TRANG
# ============================================================
st.set_page_config(
    page_title="Lịch Sử Việt Nam AI",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS — GEMINI STYLE (TỐI GIẢN, DARK THEME)
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600&display=swap');

    /* ===== RESET & FONT ===== */
    #MainMenu, footer, header,
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    .stDeployButton {
        display: none !important;
        visibility: hidden !important;
    }

    * {
        font-family: 'Google Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* ===== BACKGROUND ===== */
    .stApp {
        background: #131314 !important;
    }

    /* ===== SIDEBAR — GEMINI STYLE ===== */
    section[data-testid="stSidebar"] {
        background: #1e1f20 !important;
        border-right: 1px solid #2d2e2f !important;
        min-width: 260px !important;
        max-width: 260px !important;
    }

    section[data-testid="stSidebar"] .block-container,
    section[data-testid="stSidebar"] > div {
        padding-top: 16px !important;
    }

    /* Nút toggle sidebar */
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarExpandButton"],
    [data-testid="collapsedControl"] button {
        color: #c4c7c5 !important;
        background: transparent !important;
        border: none !important;
    }
    button[data-testid="stSidebarCollapseButton"]:hover,
    button[data-testid="stSidebarExpandButton"]:hover,
    [data-testid="collapsedControl"] button:hover {
        color: #e3e3e3 !important;
        background: #282a2c !important;
        border-radius: 50% !important;
    }
    [data-testid="collapsedControl"] {
        background: transparent !important;
        color: #c4c7c5 !important;
    }

    /* Sidebar label */
    .sidebar-label {
        font-size: 12px;
        color: #8e918f;
        font-weight: 500;
        padding: 8px 16px 6px 16px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Sidebar Streamlit button overrides */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        border-radius: 20px !important;
        color: #c4c7c5 !important;
        font-size: 14px !important;
        font-weight: 400 !important;
        padding: 10px 16px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        transition: all 0.15s ease !important;
        width: 100% !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #282a2c !important;
        color: #e3e3e3 !important;
        border: none !important;
    }
    /* Active conversation button — primary type */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: #2a3a50 !important;
        color: #a8c7fa !important;
        font-weight: 500 !important;
        border: none !important;
    }

    /* Sidebar divider */
    section[data-testid="stSidebar"] hr {
        border-color: #2d2e2f !important;
        margin: 8px 12px !important;
    }

    /* ===== MAIN CONTENT — CĂN GIỮA ===== */
    .main .block-container,
    .stAppViewBlockContainer {
        max-width: 780px !important;
        padding: 20px 20px 200px 20px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    /* ===== WELCOME SCREEN ===== */
    .welcome-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 50vh;
        text-align: center;
        margin-top: -50px;
    }

    .welcome-greeting {
        font-size: 44px;
        font-weight: 500;
        background: -webkit-linear-gradient(16deg, #4b90ff, #ff5546);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
        line-height: 1.2;
    }

    .welcome-sub {
        font-size: 40px;
        color: #e3e3e3;
        font-weight: 500;
        margin-bottom: 50px;
    }

    /* ===== SUGGESTION PILLS ===== */
    .suggestions-row {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        justify-content: center;
        max-width: 700px;
        margin: 0 auto;
    }

    div[data-testid="stHorizontalBlock"] {
        justify-content: center !important;
        gap: 10px !important;
    }

    /* Main area suggestion buttons */
    .main .stButton > button {
        background-color: #1e1f20 !important;
        border: 1px solid #1e1f20 !important;
        border-radius: 24px !important;
        color: #c4c7c5 !important;
        font-size: 14px !important;
        font-weight: 400 !important;
        padding: 10px 20px !important;
        transition: all 0.2s ease !important;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }

    .main .stButton > button:hover {
        background-color: #282a2c !important;
        border-color: #282a2c !important;
        color: #e3e3e3 !important;
    }

    /* ===== CHAT MESSAGES ===== */
    div[data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 20px 0 !important;
        max-width: 800px !important;
        margin: 0 auto !important;
    }

    div[data-testid="stChatMessage"] .stMarkdown p {
        color: #e3e3e3 !important;
        font-size: 16px !important;
        line-height: 1.6 !important;
    }

    /* Avatar */
    div[data-testid="stChatMessage"] [data-testid="stAvatar"],
    div[data-testid="stChatMessage"] .stAvatar {
        width: 36px !important;
        height: 36px !important;
        border-radius: 50% !important;
    }

    /* ===== CHAT INPUT ===== */
    div[data-testid="stChatInput"] {
        max-width: 750px !important;
        margin: 0 auto !important;
    }

    /* Textarea */
    div[data-testid="stChatInput"] textarea {
        background-color: #1e1f20 !important;
        border: 1px solid #3c4043 !important;
        border-radius: 28px !important;
        color: #e3e3e3 !important;
        font-size: 16px !important;
        padding: 18px 60px 18px 24px !important;
        min-height: 60px !important;
        width: 100% !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        transition: all 0.3s ease !important;
    }

    div[data-testid="stChatInput"] textarea:focus {
        background-color: #282a2c !important;
        border-color: #5f6368 !important;
        outline: none !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5) !important;
    }

    /* Bottom container — Gemini style */
    div[data-testid="stBottom"] {
        background: #131314 !important;
        border-top: none !important;
    }

    div[data-testid="stBottomBlockContainer"] {
        max-width: 780px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding: 16px 20px 24px 20px !important;
        background: #131314 !important;
    }

    /* Nút Gửi */
    div[data-testid="stChatInput"] button {
        background: transparent !important;
        color: #c4c7c5 !important;
        right: 15px !important;
        bottom: 12px !important;
    }

    div[data-testid="stChatInput"] button:hover {
        color: #e3e3e3 !important;
        background: #3c4043 !important;
        border-radius: 50%;
    }

    /* ===== EXPANDER (ẩn) ===== */
    div[data-testid="stExpander"] {
        background-color: #1e1f20 !important;
        border: none !important;
        border-radius: 16px !important;
        margin-top: 12px !important;
    }
    div[data-testid="stExpander"] summary {
        color: #c4c7c5 !important;
    }
    .src-chip {
        display: inline-block;
        background: #282a2c;
        color: #a8c7fa;
        font-size: 12px;
        padding: 6px 14px;
        border-radius: 16px;
        margin: 4px 6px 4px 0;
    }
</style>
""", unsafe_allow_html=True)



# ============================================================
# SESSION STATE — HỖ TRỢ NHIỀU CUỘC TRÒ CHUYỆN
# ============================================================
if "conversations" not in st.session_state:
    st.session_state.conversations = {}

if "current_conv_id" not in st.session_state:
    st.session_state.current_conv_id = None

# Inject JS để fix sidebar đóng/mở căn giữa
components.html("""
<script>
(function() {
    const doc = window.parent.document;
    
    // Tạo style tag để inject vào parent
    let styleEl = doc.getElementById('sidebar-fix-style');
    if (!styleEl) {
        styleEl = doc.createElement('style');
        styleEl.id = 'sidebar-fix-style';
        doc.head.appendChild(styleEl);
    }
    
    function updateLayout() {
        const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
        const isExpanded = sidebar && sidebar.getAttribute('aria-expanded') === 'true';
        
        if (isExpanded) {
            styleEl.textContent = '';
        } else {
            styleEl.textContent = `
                .stMain {
                    margin-left: 0px !important;
                    width: 100% !important;
                }
                div[data-testid="stBottom"] {
                    left: 0px !important;
                    width: 100% !important;
                }
            `;
        }
    }
    
    updateLayout();
    setInterval(updateLayout, 150);
    
    const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
    if (sidebar) {
        new MutationObserver(updateLayout).observe(sidebar, {
            attributes: true, attributeFilter: ['aria-expanded']
        });
    }
})();
</script>
""", height=0)

def get_current_messages():
    """Lấy messages của cuộc trò chuyện hiện tại."""
    cid = st.session_state.current_conv_id
    if cid and cid in st.session_state.conversations:
        return st.session_state.conversations[cid]["messages"]
    return []

def create_new_conversation():
    """Tạo cuộc trò chuyện mới."""
    conv_id = f"conv_{int(time.time() * 1000)}"
    st.session_state.conversations[conv_id] = {
        "title": "Cuộc trò chuyện mới",
        "messages": []
    }
    st.session_state.current_conv_id = conv_id
    clear_history_pg(session_id=conv_id)
    return conv_id

def generate_title(question: str) -> str:
    """Tạo tiêu đề ngắn gọn từ câu hỏi đầu tiên."""
    title = question.strip()
    for prefix in ["hãy ", "cho tôi biết ", "tóm tắt ", "giải thích ", "kể về ", "nói về ", "trình bày "]:
        if title.lower().startswith(prefix):
            title = title[len(prefix):]
            break
    if len(title) > 40:
        title = title[:37] + "..."
    return title.capitalize() if title else "Cuộc trò chuyện mới"

# ============================================================
# SIDEBAR — LỊCH SỬ TRÒ CHUYỆN
# ============================================================
with st.sidebar:
    # Nút tạo cuộc trò chuyện mới
    if st.button("✏️  Cuộc trò chuyện mới", key="new_chat_btn", use_container_width=True):
        create_new_conversation()
        st.rerun()

    st.markdown("---")

    # Hiển thị danh sách cuộc trò chuyện
    if st.session_state.conversations:
        st.markdown('<div class="sidebar-label">Cuộc trò chuyện</div>', unsafe_allow_html=True)

        sorted_convs = sorted(
            st.session_state.conversations.items(),
            key=lambda x: x[0],
            reverse=True
        )

        for conv_id, conv_data in sorted_convs:
            title = conv_data.get("title", "Cuộc trò chuyện mới")
            is_active = (conv_id == st.session_state.current_conv_id)
            btn_type = "primary" if is_active else "secondary"

            if st.button(
                f"💬 {title}",
                key=f"sidebar_{conv_id}",
                use_container_width=True,
                type=btn_type
            ):
                st.session_state.current_conv_id = conv_id
                st.rerun()

# ============================================================
# NỘI DUNG CHÍNH
# ============================================================
current_messages = get_current_messages()

# MÀN HÌNH WELCOME
if not current_messages:
    user_name = "Bạn"

    st.markdown(f"""
    <div class="welcome-container">
        <div class="welcome-greeting">✨ Xin chào {user_name}!</div>
        <div class="welcome-sub">Chúng ta nên bắt đầu từ đâu nhỉ?</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="suggestions-row">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.2])

    with col1:
        if st.button("⚔️ Trận Bạch Đằng", use_container_width=True, key="sug1"):
            st.session_state["pending_question"] = "Trận Bạch Đằng năm 938 diễn ra thế nào?"
    with col2:
        if st.button("🏔️ Điện Biên Phủ", use_container_width=True, key="sug2"):
            st.session_state["pending_question"] = "Tóm tắt chiến dịch Điện Biên Phủ 1954"
    with col3:
        if st.button("✈️ Hà Nội 1972", use_container_width=True, key="sug3"):
            st.session_state["pending_question"] = "Trận Hà Nội 12 ngày đêm 1972 diễn biến ra sao?"
    with col4:
        if st.button("🇻🇳 Cách mạng Tháng 8", use_container_width=True, key="sug4"):
            st.session_state["pending_question"] = "Cách mạng Tháng Tám 1945 có ý nghĩa gì?"

    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# HIỂN THỊ LỊCH SỬ CHAT
# ============================================================
for msg in current_messages:
    avatar = "👤" if msg["role"] == "user" else "✨"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ============================================================
# XỬ LÝ CÂU HỎI
# ============================================================
def process_question(question: str):
    """Xử lý câu hỏi: tạo conv nếu cần, gửi → nhận → lưu."""
    if not st.session_state.current_conv_id or st.session_state.current_conv_id not in st.session_state.conversations:
        create_new_conversation()

    conv_id = st.session_state.current_conv_id
    conv = st.session_state.conversations[conv_id]

    conv["messages"].append({"role": "user", "content": question})

    # Cập nhật tiêu đề nếu là câu hỏi đầu tiên
    if len([m for m in conv["messages"] if m["role"] == "user"]) == 1:
        conv["title"] = generate_title(question)

    with st.spinner("Đang suy nghĩ..."):
        response = ask_pg(question, session_id=conv_id)

    msg_data = {"role": "assistant", "content": response["answer"]}
    if response.get("sources"):
        msg_data["sources"] = response["sources"]
    if response.get("evaluation"):
        msg_data["evaluation"] = response["evaluation"]
    conv["messages"].append(msg_data)

# Xử lý nếu bấm nút gợi ý
if "pending_question" in st.session_state:
    q = st.session_state.pop("pending_question")
    process_question(q)
    st.rerun()

# Input Chat chính
if prompt := st.chat_input("Nhập câu hỏi về lịch sử Việt Nam..."):
    process_question(prompt)
    st.rerun()