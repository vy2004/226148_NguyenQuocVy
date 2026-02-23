import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.rag_chain_pg import ask_pg, clear_history_pg, get_stats

# Cấu hình trang
st.set_page_config(
    page_title="Chatbot Lịch Sử Việt Nam",
    page_icon="🇻🇳",
    layout="centered"
)

# ============================================================
# CSS TÙY CHỈNH - THEME CỜ VIỆT NAM (ĐỎ - VÀNG)
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ===== THEME CHÍNH ===== */
    :root {
        --vn-red: #DA251D;
        --vn-red-dark: #B71C1C;
        --vn-red-light: #E53935;
        --vn-yellow: #FFCD00;
        --vn-yellow-light: #FFD740;
        --vn-gold: #FFB300;
        --bg-dark: #0a0a0f;
        --bg-card: #12121a;
        --bg-sidebar: #0d0d14;
        --text-primary: #f0f0f0;
        --text-secondary: #a0a0a0;
        --border-color: #2a2a35;
    }

    * { font-family: 'Inter', sans-serif !important; }

    /* ===== HEADER / TIÊU ĐỀ ===== */
    .vn-header {
        text-align: center;
        padding: 25px 20px 10px 20px;
        position: relative;
    }
    .vn-header .flag-icon {
        font-size: 2.8rem;
        display: block;
        margin-bottom: 8px;
        filter: drop-shadow(0 0 10px rgba(218, 37, 29, 0.4));
    }
    .vn-header h1 {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, var(--vn-yellow), var(--vn-gold), var(--vn-yellow-light));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .vn-header .subtitle {
        color: var(--text-secondary);
        font-size: 0.9rem;
        margin-top: 6px;
        font-weight: 400;
    }
    .vn-header .red-line {
        width: 80px;
        height: 3px;
        background: linear-gradient(90deg, transparent, var(--vn-red), transparent);
        margin: 12px auto 0 auto;
        border-radius: 2px;
    }

    /* ===== WELCOME BOX ===== */
    .welcome-box {
        text-align: center;
        padding: 45px 30px;
        border-radius: 16px;
        background: linear-gradient(145deg, #1a0a0a, #12121a);
        border: 1px solid rgba(218, 37, 29, 0.2);
        margin: 25px auto;
        max-width: 620px;
        position: relative;
        overflow: hidden;
    }
    .welcome-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--vn-red), var(--vn-yellow), var(--vn-red));
    }
    .welcome-box .star {
        font-size: 3.5rem;
        margin-bottom: 15px;
        display: block;
        filter: drop-shadow(0 0 15px rgba(255, 205, 0, 0.5));
    }
    .welcome-box .greeting {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--vn-yellow);
        margin-bottom: 10px;
    }
    .welcome-box .desc {
        color: var(--text-secondary);
        font-size: 0.95rem;
        line-height: 1.7;
    }
    .welcome-box .desc b {
        color: var(--vn-yellow-light);
    }
    .welcome-box .tags {
        margin-top: 20px;
        display: flex;
        justify-content: center;
        gap: 8px;
        flex-wrap: wrap;
    }
    .welcome-box .tag {
        background: rgba(218, 37, 29, 0.15);
        border: 1px solid rgba(218, 37, 29, 0.3);
        color: #ff8a80;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 500;
    }

    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0a0a, #0d0d14) !important;
        border-right: 1px solid rgba(218, 37, 29, 0.15) !important;
    }

    .sidebar-brand {
        text-align: center;
        padding: 10px 0 5px 0;
    }
    .sidebar-brand .logo {
        font-size: 2.2rem;
        margin-bottom: 5px;
        display: block;
    }
    .sidebar-brand .name {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--vn-yellow);
    }
    .sidebar-brand .tagline {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-top: 2px;
    }

    /* Status badge */
    .status-badge {
        display: flex;
        align-items: center;
        gap: 8px;
        background: rgba(218, 37, 29, 0.1);
        border: 1px solid rgba(218, 37, 29, 0.25);
        border-radius: 10px;
        padding: 10px 14px;
        margin: 10px 0;
    }
    .status-badge .dot {
        width: 8px;
        height: 8px;
        background: #4caf50;
        border-radius: 50%;
        box-shadow: 0 0 6px #4caf50;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    .status-badge .label {
        color: var(--text-primary);
        font-size: 0.82rem;
        font-weight: 500;
    }

    /* Stats grid */
    .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin: 10px 0;
    }
    .stat-card {
        background: rgba(255, 205, 0, 0.05);
        border: 1px solid rgba(255, 205, 0, 0.12);
        border-radius: 10px;
        padding: 12px 10px;
        text-align: center;
    }
    .stat-card .stat-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--vn-yellow);
    }
    .stat-card .stat-label {
        font-size: 0.7rem;
        color: var(--text-secondary);
        margin-top: 2px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Section title */
    .section-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--vn-yellow);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 15px 0 8px 0;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .section-title::after {
        content: '';
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, rgba(218, 37, 29, 0.3), transparent);
    }

    /* Suggestion buttons */
    .suggestion-btn button {
        border: 1px solid var(--border-color) !important;
        border-radius: 10px !important;
        background: rgba(218, 37, 29, 0.05) !important;
        transition: all 0.3s ease !important;
        text-align: left !important;
        font-size: 0.85rem !important;
    }
    .suggestion-btn button:hover {
        border-color: var(--vn-red) !important;
        background: rgba(218, 37, 29, 0.12) !important;
        transform: translateX(3px);
    }

    /* Delete button */
    .delete-btn button {
        border: 1px solid rgba(218, 37, 29, 0.3) !important;
        color: #ff8a80 !important;
        border-radius: 10px !important;
    }
    .delete-btn button:hover {
        background: rgba(218, 37, 29, 0.15) !important;
        border-color: var(--vn-red) !important;
    }

    /* ===== CHAT MESSAGES ===== */
    .stChatMessage {
        max-width: 3000px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    .stChatInput {
        max-width: 3000px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    /* ===== FOOTER ===== */
    .sidebar-footer {
        text-align: center;
        padding: 15px 0;
        border-top: 1px solid var(--border-color);
        margin-top: 15px;
    }
    .sidebar-footer .version {
        font-size: 0.7rem;
        color: var(--text-secondary);
    }
    .sidebar-footer .flag {
        font-size: 1.5rem;
        margin-bottom: 5px;
        display: block;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="vn-header">
    <span class="flag-icon">🇻🇳</span>
    <h1>Chatbot Lịch Sử Việt Nam</h1>
    <div class="subtitle">Hệ thống tra cứu lịch sử thông minh bằng AI</div>
    <div class="red-line"></div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    # Brand
    st.markdown("""
    <div class="sidebar-brand">
        <span class="logo">🇻🇳</span>
        <div class="name">Lịch Sử Việt Nam</div>
        <div class="tagline">Tra cứu • Hỏi đáp • Khám phá</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Câu hỏi gợi ý
    st.markdown("""
    <div class="section-title">⭐ Câu hỏi gợi ý</div>
    """, unsafe_allow_html=True)

    suggestions = [
        "🗡️ Trận Bạch Đằng năm 938 diễn ra thế nào?",
        "👩 Khởi nghĩa Hai Bà Trưng có ý nghĩa gì?",
        "⚔️ Chiến dịch Điện Biên Phủ ra sao?",
        "🏴 Cách mạng Tháng Tám 1945 là gì?",
        "🛡️ Nhà Trần chống quân Nguyên Mông?",
        "✈️ Trận Hà Nội 12 ngày đêm?",
    ]
    for s in suggestions:
        st.markdown('<div class="suggestion-btn">', unsafe_allow_html=True)
        if st.button(s, use_container_width=True):
            # Lấy phần text sau emoji
            st.session_state["pending_question"] = s.split(" ", 1)[1] if s[0] in "🗡👩⚔🏴🛡✈" else s
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # Xóa lịch sử
    st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True, type="secondary"):
        clear_history_pg("streamlit_session")
        st.session_state.messages = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="sidebar-footer">
        <span class="flag">🇻🇳</span>
        <div class="version">Đồ án 2 — Chatbot Lịch Sử v2.0</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# CHAT AREA
# ============================================================

# Khởi tạo session
if "messages" not in st.session_state:
    st.session_state.messages = []

# Welcome message
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-box">
        <span class="star">⭐</span>
        <div class="greeting">Xin chào! 🇻🇳</div>
        <div class="desc">
            Tôi là trợ lý AI chuyên về <b>Lịch Sử Việt Nam</b><br>
            Từ thời <b>Văn Lang – Âu Lạc</b> đến <b>thời kỳ hiện đại</b><br><br>
            Hãy hỏi tôi về bất kỳ sự kiện, nhân vật,<br>
            trận đánh hay triều đại nào bạn quan tâm!
        </div>
        <div class="tags">
            <span class="tag">🏛️ Triều đại</span>
            <span class="tag">⚔️ Trận đánh</span>
            <span class="tag">👤 Nhân vật</span>
            <span class="tag">📜 Sự kiện</span>
            <span class="tag">🗺️ Địa danh</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("📚 Nguồn tham khảo"):
                for src in msg["sources"]:
                    st.write(f"- {src}")
        if msg.get("crawl_info"):
            with st.expander("🔍 Thông tin crawl"):
                info = msg["crawl_info"]
                st.write(f"- **Chunk mới:** {info.get('new_chunks', 0)}")
        if msg.get("evaluation"):
            with st.expander("📊 Đánh giá context"):
                eval_info = msg["evaluation"]
                st.write(f"- **Đủ context:** {'✅' if eval_info['sufficient'] else '❌'}")
                st.write(f"- **Độ tin cậy:** {eval_info['confidence']}")

# Hàm xử lý câu hỏi
def process_question(question):
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("🔍 Đang tìm kiếm trong kho tri thức lịch sử..."):
            response = ask_pg(question, session_id="streamlit_session")

        st.markdown(response["answer"])

        msg_data = {"role": "assistant", "content": response["answer"]}

        if response.get("sources"):
            with st.expander("📚 Nguồn tham khảo"):
                for src in response["sources"]:
                    st.write(f"- {src}")
            msg_data["sources"] = response["sources"]

        if response.get("crawl_info"):
            with st.expander("🔍 Thông tin crawl"):
                info = response["crawl_info"]
                st.write(f"- **Chunk mới:** {info.get('new_chunks', 0)}")
            msg_data["crawl_info"] = response["crawl_info"]

        if response.get("evaluation"):
            with st.expander("📊 Đánh giá context"):
                eval_info = response["evaluation"]
                st.write(f"- **Đủ context:** {'✅' if eval_info['sufficient'] else '❌'}")
                st.write(f"- **Độ tin cậy:** {eval_info['confidence']}")
            msg_data["evaluation"] = response["evaluation"]

        st.session_state.messages.append(msg_data)

# Xử lý câu hỏi từ gợi ý
if "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")
    process_question(question)
    st.rerun()

# Xử lý input từ chat box
if question := st.chat_input("💬 Nhập câu hỏi về lịch sử Việt Nam..."):
    process_question(question)