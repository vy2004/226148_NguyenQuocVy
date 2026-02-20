import streamlit as st
import sys
import os
import uuid

# Thêm đường dẫn
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.join(project_dir, 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

from rag_chain import HistoryChatbot

# ==================== CẤU HÌNH ====================
st.set_page_config(
    page_title="Chatbot Lịch Sử Việt Nam",
    page_icon="🏛️",
    layout="wide"
)
#======================KHÔNG TỰ ĐỘNG DỊCH=======================
st.markdown("""
<meta name="google" content="notranslate">
<style>
    body { -webkit-locale: "vi"; }
</style>
""", unsafe_allow_html=True)

# ==================== KHỞI TẠO ====================
@st.cache_resource
def load_chatbot():
    return HistoryChatbot()

try:
    chatbot = load_chatbot()
except Exception as e:
    st.error(f"❌ Lỗi khởi tạo chatbot: {e}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("🏛️ Chatbot Lịch Sử")
    st.markdown("Tra cứu thông tin lịch sử Việt Nam")
    
    st.markdown("---")
    
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        chatbot.clear_session(st.session_state.session_id)
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 💡 Câu hỏi gợi ý")
    suggestions = [
        "Trận Bạch Đằng năm 938 diễn ra như thế nào?",
        "Khởi nghĩa Hai Bà Trưng có ý nghĩa gì?",
        "Chiến dịch Điện Biên Phủ diễn ra năm nào?",
        "Nhà Trần đã chống quân Mông Nguyên ra sao?",
    ]
    for i, s in enumerate(suggestions):
        if st.button(f"📌 {s}", key=f"sug_{i}", use_container_width=True):
            st.session_state.suggestion_query = s

# ==================== TIÊU ĐỀ ====================
st.title("🏛️ Chatbot Tra Cứu Lịch Sử Việt Nam")
st.caption("🤖 Được hỗ trợ bởi AI - Dữ liệu từ tài liệu lịch sử Việt Nam")

# Tin nhắn chào mừng nếu chưa có tin nhắn
if not st.session_state.messages:
    st.info("""👋 Xin chào! Tôi là **Trợ lý Lịch sử Việt Nam**.
    
Tôi có thể giúp bạn tra cứu:  🏰 Triều đại phong kiến  |  ⚔️ Trận đánh  |  👑 Nhân vật lịch sử

Hãy nhập câu hỏi bên dưới hoặc chọn gợi ý ở thanh bên trái!""")

# ==================== HIỂN THỊ LỊCH SỬ ====================
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="🧑"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📚 Nguồn tham khảo"):
                    for source in msg["sources"]:
                        st.markdown(f"- 📄 {source}")

# ==================== NHẬN INPUT ====================
# Lấy query từ gợi ý hoặc chat input
suggestion_query = st.session_state.pop("suggestion_query", None)
user_input = st.chat_input("💬 Nhập câu hỏi về lịch sử Việt Nam...")
query = suggestion_query or user_input

# ==================== XỬ LÝ CÂU HỎI ====================
if query:
    # Hiển thị câu hỏi
    with st.chat_message("user", avatar="🧑"):
        st.markdown(query)
    
    # Gọi chatbot và hiển thị kết quả
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("⏳ Đang tìm kiếm và phân tích..."):
            result = chatbot.chat(query, session_id=st.session_state.session_id)
        
        st.markdown(result["answer"])
        if result.get("sources"):
            with st.expander("📚 Nguồn tham khảo"):
                for source in result["sources"]:
                    st.markdown(f"- 📄 {source}")
    
    # Lưu vào lịch sử
    st.session_state.messages.append({"role": "user", "content": query})
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result.get("sources", [])
    })