# 🏛️ Chatbot Tra Cứu Lịch Sử Việt Nam

Chatbot sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)** để tra cứu thông tin lịch sử Việt Nam từ các tài liệu văn bản.

## 📋 Mô tả

- **Backend:** Python, ChromaDB, Groq/Gemini API
- **Frontend:** Streamlit
- **Kỹ thuật:** RAG (Retrieval-Augmented Generation)
- **Dữ liệu:** 14 tài liệu lịch sử Việt Nam từ thời cổ đại đến hiện đại

## 📁 Cấu trúc Project

```
DoAn2-ChatbotLichSu/
├── backend/
│   ├── config.py          # Cấu hình
│   ├── vector_store.py    # Tìm kiếm vector
│   ├── rag_chain.py       # Logic chatbot
│   └── api.py             # FastAPI server
├── data/
│   └── raw/               # 14 tài liệu lịch sử
├── data_processing/
│   ├── loader.py           # Đọc tài liệu
│   ├── chunking.py         # Chia nhỏ tài liệu
│   ├── indexing.py          # Tạo vector database
│   └── run_pipeline.py     # Chạy pipeline
├── frontend/
│   └── app.py             # Giao diện Streamlit
├── evaluation/
│   └── evaluate.py        # Đánh giá chatbot
├── .env                   # API keys (không push)
├── .gitignore
├── requirements.txt
└── README.md
```

## 🚀 Cài đặt và Chạy

### 1. Clone repository
```bash
git clone https://github.com/vy2004/226148_NguyenQuocVy.git
cd DoAn2-ChatbotLichSu
```

### 2. Tạo môi trường ảo
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### 4. Cấu hình API Key
Tạo file `.env` trong thư mục gốc:
```
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
```

### 5. Chạy Pipeline (tạo vector database)
```bash
cd data_processing
python run_pipeline.py
```

### 6. Chạy Frontend
```bash
cd ..
streamlit run frontend/app.py
```

## 🛠️ Công nghệ sử dụng

| Công nghệ | Mục đích |
|-----------|----------|
| Python 3.13 | Ngôn ngữ chính |
| ChromaDB | Vector database |
| Groq API (LLaMA 3.3 70B) | LLM sinh câu trả lời |
| Streamlit | Giao diện web |
| Sentence-Transformers | Embedding văn bản |

## 👨‍💻 Tác giả

- **Họ tên:** Nguyễn Quốc Vỹ
- **MSSV:** 226148
- Hiện tại thì project này của em chưa hoàn chỉnh, em sẽ bổ sung những gì còn thiếu xót và sẽ cố gắng để hoàn thành kịp tiến độ của Đồ án 2. Em cảm ơn.