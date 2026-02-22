Chatbot Tra Cứu Lịch Sử Việt Nam
Giới thiệu
Chatbot Tra Cứu Lịch Sử Việt Nam là một hệ thống hỏi đáp lịch sử Việt Nam, sử dụng mô hình RAG (Retrieval-Augmented Generation) kết hợp với cơ sở dữ liệu vector trên nền tảng PostgreSQL. Chatbot có thể trả lời các câu hỏi về sự kiện, nhân vật, địa danh, và các giai đoạn lịch sử Việt Nam từ thời cổ đại đến hiện đại.

Nguồn dữ liệu: Wikipedia, các trang web lịch sử, tài liệu PDF/text.
Lưu trữ: Toàn bộ dữ liệu được lưu dưới dạng vector embedding trong PostgreSQL (không cần extension pgvector).
Tìm kiếm: Sử dụng cosine similarity để tìm các đoạn tài liệu liên quan nhất cho mỗi câu hỏi.
LLM: Hỗ trợ Groq API hoặc Google Gemini API để sinh câu trả lời tự nhiên, chính xác.
Lịch sử chat: Lưu lại toàn bộ câu hỏi và câu trả lời của người dùng.
⚙️ Tóm tắt hoạt động của chatbot
Người dùng nhập câu hỏi về lịch sử Việt Nam.
Chatbot chuyển câu hỏi thành vector embedding.
Tìm kiếm các đoạn tài liệu liên quan nhất trong PostgreSQL bằng cosine similarity.
Tổng hợp context từ các tài liệu tìm được.
Gửi context và câu hỏi vào LLM (Groq/Gemini) để sinh câu trả lời chi tiết.
Hiển thị câu trả lời cho người dùng, kèm nguồn tham khảo.
Lưu lịch sử chat vào bảng chat_history trong PostgreSQL.

## 📋 Mô tả

- **Backend:** Python, ChromaDB, Groq/Gemini API
- **Frontend:** Streamlit
- **Kỹ thuật:** RAG (Retrieval-Augmented Generation)
- **Dữ liệu:** 14 tài liệu lịch sử Việt Nam từ thời cổ đại đến hiện đại

DoAn2-ChatbotLichSu/
├── backend/
│   ├── config.py
│   ├── vector_store.py
│   ├── rag_chain.py
│   ├── api.py
│   ├── db_config.py              # ← Cấu hình kết nối PostgreSQL, embedding model
│   ├── pg_vector_store.py        # ← Quản lý lưu trữ, tìm kiếm, lịch sử chat với PostgreSQL (không cần pgvector)
│   ├── rag_chain_pg.py           # ← Logic chính chatbot dùng PostgreSQL
│   ├── migrate_to_pg.py          # ← Chuyển dữ liệu từ ChromaDB sang PostgreSQL
├── data/
│   ├── raw/
│   └── processed/
├── data_processing/
│   ├── loader.py
│   ├── chunking.py
│   ├── indexing.py
│   └── run_pipeline.py
├── frontend/
│   ├── app.py
├── evaluation/
├── chroma_db/
├── .env
├── .gitignore
├── requirements.txt
└── README.md

### `backend/` — Xử lý logic chatbot và API
File	                                        Chức năng
config.py	                        Đọc API key (Groq/Gemini) từ .env, cấu hình đường dẫn ChromaDB tên collection, số kết quả tìm kiếm, chọn LLM (Groq hoặc Gemini)
vector_store.py	                    Kết nối ChromaDB, tìm kiếm tài liệu liên quan theo câu hỏi, lọc theo độ tương đồng (cosine similarity), trả về context và danh sách nguồn
rag_chain.py	                    Logic chính của chatbot: xây dựng prompt, gọi LLM (Groq/Gemini) để sinh câu trả lời, quản lý lịch sử hội thoại theo session, trích xuất nguồn tham khảo từ câu trả lời
api.py	                            Cung cấp REST API bằng FastAPI với 2 endpoint: POST /chat (gửi câu hỏi, nhận câu trả lời) và POST /clear (xóa lịch sử chat)
db_config.py	                    Cấu hình kết nối PostgreSQL và embedding model
pg_vector_store.py	                Quản lý lưu trữ, tìm kiếm, lịch sử chat với PostgreSQL (không cần pgvector)
rag_chain_pg.py	                    Logic chính chatbot dùng PostgreSQL: nhận câu hỏi, tìm context, gọi LLM, trả lời, lưu lịch sử chat. Tự động crawl thêm dữ liệu nếu thiếu context.
migrate_to_pg.py	                Chuyển dữ liệu từ ChromaDB sang PostgreSQL. Chạy 1 lần sau khi cài đặt PostgreSQL để migrate dữ liệu cũ.

### `data_processing/` — Xử lý dữ liệu đầu vào

| File | Chức năng |
|------|-----------|
| `loader.py` | Đọc tất cả file `.txt` từ thư mục `data/raw/`, trả về danh sách document gồm nội dung, tên file và đường dẫn |
| `chunking.py` | Chia nhỏ mỗi tài liệu thành các chunk (800 ký tự, overlap 200), lưu kết quả ra file `chunks.json` kèm metadata (nguồn, thứ tự chunk) |
| `indexing.py` | Tạo vector database trên ChromaDB từ danh sách chunks, hỗ trợ test tìm kiếm với các câu hỏi mẫu |
| `run_pipeline.py` | Chạy tuần tự toàn bộ pipeline: đọc tài liệu → chia chunk → lưu JSON → tạo vector database → test tìm kiếm |

### `data/` — Dữ liệu lịch sử

| Thư mục/File | Chức năng |
|--------------|-----------|
| `raw/` | Chứa các file `.txt` gốc về các sự kiện lịch sử Việt Nam (Bạch Đằng 938, Hai Bà Trưng, Nhà Lý, Nhà Trần, Điện Biên Phủ, Cách mạng Tháng Tám, Kháng chiến chống Mỹ,...) |
| `processed/chunks.json` | Kết quả sau khi chia nhỏ tài liệu, gồm text và metadata của từng chunk, dùng làm đầu vào cho vector database |

### `frontend/` — Giao diện người dùng

| File | Chức năng |
|------|-----------|
| `app.py` | Giao diện web Streamlit: hiển thị khung chat, câu hỏi gợi ý ở sidebar, nút xóa lịch sử, hiển thị câu trả lời kèm nguồn tham khảo, quản lý session chat |

### `chroma_db/` — Vector database

| Nội dung | Chức năng |
|----------|-----------|
| `chroma.sqlite3` + thư mục con | Lưu trữ vector embeddings của các chunk, được ChromaDB tự động tạo và quản lý. Có thể tái tạo bằng cách chạy lại pipeline |

### File gốc

| File | Chức năng |
|------|-----------|
| `.env` | Lưu API key của Groq và Gemini (không push lên git) |
| `.gitignore` | Loại trừ `venv/`, `.env`, `__pycache__/`, `chroma_db/` khỏi git |
| `requirements.txt` | Danh sách thư viện Python cần cài đặt |
| `README.md` | Tài liệu hướng dẫn project |

## Cài đặt và Chạy

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

## Công nghệ sử dụng

| Công nghệ | Mục đích |
|-----------|----------|
| Python 3.13 | Ngôn ngữ chính |
| ChromaDB | Vector database |
| Groq API (LLaMA 3.3 70B) | LLM sinh câu trả lời |
| Streamlit | Giao diện web |
| Sentence-Transformers | Embedding văn bản |

## Tác giả

- **Họ tên:** Nguyễn Quốc Vỹ
- **MSSV:** 226148
- Hiện tại thì project này của em chưa hoàn chỉnh, em sẽ bổ sung những gì còn thiếu xót và sẽ cố gắng để hoàn thành kịp tiến độ của Đồ án 2. Em cảm ơn.