import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Dùng PostgreSQL thay ChromaDB
try:
    from backend.rag_chain_pg import ask_pg as ask_v2, clear_history_pg as clear_history_v2, get_stats
    USE_PG = True
    print("✅ Đang dùng PostgreSQL")
except ImportError:
    from backend.rag_chain_v2 import ask_v2, clear_history_v2
    USE_PG = False
    print("⚠️ Fallback: Đang dùng ChromaDB")

# Cấu hình trang
st.set_page_config(
    page_title="Chatbot Lịch Sử Việt Nam",
    page_icon="🏛️",
    layout="centered"  # ← Đổi từ "wide" sang "centered"
)

# CSS tùy chỉnh - căn giữa và đẹp hơn
st.markdown("""
<style>
    /* Căn giữa tiêu đề */
    .main-title {
        text-align: center;
        padding: 20px 0 5px 0;
    }
    .main-title h1 {
        font-size: 2.5rem;
        background: linear-gradient(135deg, #FFD700, #FFA500);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    .main-caption {
        text-align: center;
        color: #888;
        font-size: 1rem;
        margin-bottom: 30px;
    }
    
    /* Welcome message căn giữa */
    .welcome-box {
        text-align: center;
        padding: 40px 20px;
        border-radius: 15px;
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #333;
        margin: 20px auto;
        max-width: 600px;
    }
    .welcome-box .icon {
        font-size: 4rem;
        margin-bottom: 15px;
    }
    .welcome-box .text {
        color: #ccc;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    
    /* Chat container */
    .stChatMessage {
        max-width: 3000px;
        margin: 0 auto;
    }
    
    /* Chat input căn giữa */
    .stChatInput {
        max-width: 3000px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    
    /* Sidebar đẹp hơn */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0e1117, #1a1a2e);
    }
    
    /* Nút gợi ý */
    .suggestion-btn button {
        border: 1px solid #333 !important;
        border-radius: 10px !important;
    }
    .suggestion-btn button:hover {
        border-color: #FFD700 !important;
        background: #1a1a2e !important;
    }
            /* Chat container */
    .stChatMessage {
        max-width: 3000px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    .stChatMessage[data-testid="stChatMessage-assistant"] > div {
        max-width: 3000px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
</style>
""", unsafe_allow_html=True)

# Tiêu đề căn giữa
st.markdown("""
<div class="main-title">
    <h1>🏛️ Chatbot Tra Cứu Lịch Sử Việt Nam</h1>
</div>
<div class="main-caption">
    Hỏi đáp về lịch sử Việt Nam từ thời cổ đại đến hiện đại
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🏛️ Lịch Sử Việt Nam")
    st.divider()

    # Hiển thị trạng thái database
    if USE_PG:
        st.success("🐘 PostgreSQL đang hoạt động")
        try:
            stats = get_stats()
            col1, col2 = st.columns(2)
            col1.metric("📦 Chunks", stats["total_chunks"])
            col2.metric("📚 Nguồn", stats["total_sources"])
            col1.metric("💬 Chat", stats["total_chats"])
            col2.metric("🌐 Crawl", stats["total_crawled"])
        except:
            pass
    else:
        st.warning("⚠️ Đang dùng ChromaDB")

    st.divider()
    st.markdown("### 📌 Câu hỏi gợi ý")
    suggestions = [
        "Trận Bạch Đằng năm 938 diễn ra như thế nào?",
        "Khởi nghĩa Hai Bà Trưng có ý nghĩa gì?",
        "Chiến dịch Điện Biên Phủ diễn ra như thế nào?",
        "Cách mạng Tháng Tám 1945 có ý nghĩa gì?",
        "Nhà Trần chống quân Nguyên Mông ra sao?",
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True):
            st.session_state["pending_question"] = s

    st.divider()
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True, type="secondary"):
        clear_history_v2("streamlit_session")
        st.session_state.messages = []
        st.rerun()

# Khởi tạo session
if "messages" not in st.session_state:
    st.session_state.messages = []

# Tin nhắn chào mừng - căn giữa đẹp
if not st.session_state.messages:
    db_type = "PostgreSQL" if USE_PG else "ChromaDB"
    st.markdown(f"""
    <div class="welcome-box">
        <div class="icon">🏛️</div>
        <div class="text">
            Xin chào! Tôi là chatbot tra cứu <b>Lịch Sử Việt Nam</b> 🇻🇳<br>
            <br><br>
            Hãy đặt câu hỏi cho tôi về bất kỳ sự kiện, nhân vật,<br>
            hay giai đoạn lịch sử nào của Việt Nam!
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
        with st.spinner("🔍 Đang tìm kiếm và phân tích..."):
            response = ask_v2(question, session_id="streamlit_session")

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