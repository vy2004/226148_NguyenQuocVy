---
title: Chatbot Lich Su Viet Nam
emoji: 📚
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Chatbot Tra Cứu Lịch Sử Việt Nam

Chatbot hỏi đáp về lịch sử Việt Nam sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)**. Hệ thống đọc tài liệu PDF, tạo embedding, truy vấn ChromaDB, gọi LLM để trả lời câu hỏi, lưu lịch sử hỏi đáp, và cung cấp giao diện Streamlit hoàn chỉnh cho người dùng.

## Demo trực tuyến

> **Github**: [https://vy2004.github.io/] **Hugging Face Space**: (https://huggingface.co/spaces/NguyenQuocVy2004/chatbot-lichsu)
>
> Truy cập link trên để sử dụng chatbot trực tiếp trên trình duyệt mà không cần cài đặt.
> Link Video Demo dự án: [https://drive.google.com/drive/folders/1m1LDyNg1uEggxRNb6YpxEEvp85VXhJC9?usp=drive_link]
---

## Tổng quan

| Thành phần | Chi tiết |
|---|---|
| Bài toán | Chatbot tra cứu lịch sử Việt Nam |
| Giao diện | Streamlit (`frontend/app.py`) |
| Backend chat | `backend/rag_chain_pg.py` |
| API bổ trợ | FastAPI (`backend/api.py`) |
| Vector DB | ChromaDB persistent tại `data/csdl_vector/` |
| Embedding | `intfloat/multilingual-e5-base` (prefix E5: `query:` / `passage:`) |
| LLM chính | Groq `llama-3.3-70b-versatile` |
| LLM dự phòng | Gemini `2.5-flash` → `2.0-flash` → `2.0-flash-lite` |
| CSDL quan hệ | SQLite tại `data/chatbot.db` |
| Nguồn dữ liệu | PDF lịch sử + Wikipedia tiếng Việt (fallback tự động) |

---

## Tính năng

### 1. Hỏi đáp RAG

- Nhận câu hỏi từ giao diện hoặc API.
- Phát hiện câu hỏi tiếp nối (follow-up) để giữ context theo session — nhận diện qua từ chỉ thị ("sự kiện này", "chi tiết hơn", ...) và câu hỏi ngắn không chứa danh từ riêng.
- Tìm ngữ cảnh liên quan trong ChromaDB bằng embedding E5 (cosine similarity).
- Ưu tiên nguồn trùng tên file (source-priority) và keyword boosting khi xếp hạng kết quả.
- Gọi Groq làm LLM chính, tự động fallback sang chuỗi Gemini (`2.5-flash` → `2.0-flash` → `2.0-flash-lite`) khi gặp lỗi hoặc rate-limit.
- Extractive fallback: trích xuất dòng liên quan nhất từ context khi cả hai LLM đều lỗi.
- Bổ sung ngữ cảnh từ Wikipedia khi kho PDF chưa đủ thông tin — tự động crawl, làm sạch, và lưu chunk vào ChromaDB để lần sau không cần crawl lại.

### 2. Quản lý tài liệu PDF

- Upload PDF trực tiếp trên giao diện Streamlit (tối đa 200 MB).
- Tóm tắt nhanh nội dung file vừa tải lên bằng LLM.
- **Index tăng dần (incremental)**: hệ thống tự động kiểm tra tài liệu đã được index chưa (`is_document_indexed()`), nếu đã có thì bỏ qua — tránh mất thời gian re-embed.
- ID chunk ổn định theo tên nguồn (`tenfile__chunk_0`, `tenfile__chunk_1`, ...) tránh ghi đè giữa các tài liệu.
- Xóa chunk theo tên file (`delete_chunks_by_source()`) khi cần index lại 1 tài liệu cụ thể.
- Admin có thể thêm/xóa tài liệu hệ thống và đồng bộ chỉ mục (chỉ tài liệu mới).
- Hỗ trợ index offline từ thư mục `data/pdf/` qua `run_pipeline.py`.

### 3. Quản lý người dùng và phân quyền

- Đăng ký, đăng nhập, đăng xuất. Chỉ chấp nhận email `@gmail.com`.
- Quên mật khẩu qua OTP 6 chữ số gửi email thật bằng Resend API (hết hạn sau 15 phút).
- Mật khẩu mã hóa SHA-256 + salt.
- Phân quyền `user` / `admin`.
- Admin có thể đổi vai trò và khóa/mở khóa tài khoản người dùng.

### 4. Quản lý hội thoại và phản hồi

- Tạo nhiều cuộc trò chuyện, tự động đặt tiêu đề từ câu hỏi đầu tiên.
- Lưu lịch sử hỏi đáp và nguồn tham khảo cho từng câu trả lời (bảng `tin_nhan_tham_khao`).
- Người dùng đánh giá 👍/👎 và gửi phản hồi chi tiết.
- Admin xem lịch sử hỏi đáp toàn hệ thống và quản lý phản hồi (trạng thái: mới / đã xem / đóng).

### 5. Trang quản trị (Admin)

- Quản lý người dùng: xem danh sách, đổi vai trò, khóa/mở khóa.
- Lịch sử hỏi đáp toàn hệ thống.
- Phản hồi người dùng: xem và cập nhật trạng thái xử lý.
- Tài liệu hệ thống: thêm/xóa PDF, đồng bộ chỉ mục ChromaDB (incremental).
- Thống kê RAG: số chunks, collection info.

### 6. Đồng bộ dữ liệu lên HF Dataset

- Tự động đồng bộ `chatbot.db` lên HF Dataset repo sau mỗi thao tác ghi (rate-limited 30s).
- Đồng bộ file PDF (`schedule_pdf_upload`, `schedule_pdf_delete`).
- Đồng bộ vector store (`schedule_vector_sync`) — upload toàn bộ `csdl_vector/`.
- Cập nhật `manifest.json` trên dataset repo để kiểm soát phiên bản.

### 7. API cơ bản

- `GET /` — kiểm tra trạng thái server.
- `POST /chat` — gửi câu hỏi và nhận câu trả lời (hỗ trợ `session_id`).
- `POST /clear` — xóa context chat theo `session_id`.
- CORS cho phép mọi origin.

---

## Kiến trúc

```text
Người dùng
   │
   ▼
Streamlit UI (frontend/app.py)
   │
   ├── Auth / Lịch sử / Feedback / Upload PDF / Admin
   │
   ▼
RAG Engine (backend/rag_chain_pg.py)
   │
   ├── Embedding search trong ChromaDB
   ├── Follow-up detection theo session
   ├── Groq → Gemini (2.5-flash → 2.0-flash → 2.0-flash-lite) → Extractive fallback
   ├── Wikipedia crawl + lưu vào ChromaDB (backend/wiki_crawler.py)
   │
   ├──▶ SQLite (backend/db.py)
   │      ├── nguoi_dung
   │      ├── khoi_phuc_mat_khau
   │      ├── cuoc_tro_chuyen
   │      ├── tin_nhan
   │      ├── tai_lieu
   │      ├── phan_hoi_nguoi_dung
   │      └── tin_nhan_tham_khao
   │
   ├──▶ ChromaDB (data/csdl_vector/)
   │
   ├──▶ PDF pipeline (data_processing/)
   │
   └──▶ HF Dataset Sync (backend/db_sync.py)
           ├── chatbot.db
           ├── pdf/
           ├── csdl_vector/
           └── manifest.json
```

---

## Cấu trúc thư mục

```text
chatbot-lichsu/
├── .streamlit/
│   └── config.toml              # Cấu hình Streamlit (theme, upload, XSRF)
├── backend/
│   ├── admin_config.py           # Danh sách email admin bootstrap
│   ├── admin_services.py         # Dịch vụ admin: user, feedback, tài liệu, reindex
│   ├── api.py                    # FastAPI endpoint cơ bản
│   ├── auth.py                   # Đăng ký, đăng nhập, OTP, reset mật khẩu
│   ├── config.py                 # Cấu hình backend (API keys, model)
│   ├── db.py                     # SQLite schema, migration, truy vấn
│   ├── db_sync.py                # Đồng bộ DB/PDF/vector lên HF Dataset repo
│   ├── email_service.py          # Gửi OTP qua Resend API (HTTP)
│   ├── rag_chain_pg.py           # RAG engine chính
│   ├── runtime_paths.py          # Quản lý đường dẫn runtime (local / Space)
│   └── wiki_crawler.py           # Crawl Wikipedia + lưu vào ChromaDB
├── data/
│   ├── chatbot.db                # SQLite database (runtime)
│   ├── csdl_vector/              # ChromaDB persistent storage
│   ├── pdf/                      # File PDF nguồn
│   └── processed/                # Dữ liệu xử lý trung gian (chunks JSON)
├── data_processing/
│   ├── chunking.py               # Chia đoạn văn bản (800 chars, overlap 200)
│   ├── dynamic_indexing.py       # Index tăng dần, kiểm tra trùng lặp
│   ├── indexing.py               # Vector DB: index, search, kiểm tra trùng, xóa theo nguồn
│   ├── loader.py                 # Đọc PDF (pypdf)
│   └── run_pipeline.py           # Pipeline index offline (chỉ index tài liệu mới)
├── frontend/
│   └── app.py                    # Giao diện Streamlit (chat, auth, admin, feedback)
├── scripts/
│   ├── bootstrap_space_data.py   # Tải dataset runtime cho HF Space
│   ├── export_dataset_bundle.py  # Xuất bundle dữ liệu cho dataset repo
│   └── start_space.py            # Entrypoint cho HF Space
├── Dockerfile                    # Docker build cho HF Space (python:3.11-slim)
├── requirements.txt
└── README.md
```

---

## Cơ sở dữ liệu

### SQLite (`data/chatbot.db`)

| Bảng | Mô tả |
|---|---|
| `nguoi_dung` | Thông tin tài khoản, vai trò (`user`/`admin`), trạng thái khóa |
| `khoi_phuc_mat_khau` | OTP đặt lại mật khẩu (6 chữ số, hết hạn 15 phút) |
| `cuoc_tro_chuyen` | Metadata mỗi cuộc trò chuyện |
| `tin_nhan` | Nội dung hỏi đáp, nguồn tham khảo, đánh giá |
| `tai_lieu` | Tài liệu người dùng và tài liệu hệ thống |
| `phan_hoi_nguoi_dung` | Đánh giá và nhận xét của người dùng |
| `tin_nhan_tham_khao` | Nguồn tham khảo chuẩn hóa gắn với từng tin nhắn |

### ChromaDB (`data/csdl_vector/`)

| Thuộc tính | Giá trị |
|---|---|
| Collection | `lich_su_viet_nam` |
| Embedding | `intfloat/multilingual-e5-base` |
| Metric | Cosine similarity |
| Chunk ID | `{source}__chunk_{i}` |
| Max chunks/query | 20 |
| Max context chars | 20,000 |

---

## Luồng xử lý chính

### Index tài liệu

```text
PDF → loader.py → kiểm tra đã index chưa (get_indexed_sources)
  ├── Đã index → bỏ qua
  └── Chưa index → chunking.py (800 chars, overlap 200)
        → indexing.py (ID: source__chunk_i)
        → kiểm tra trùng ID trong batch → upsert ChromaDB
```

- `run_pipeline.py`: lọc bỏ tài liệu đã index trước khi xử lý, chỉ index tài liệu mới.
- `process_uploaded_pdf`: kiểm tra `is_document_indexed()` trước khi index, dùng `add_new_documents()` thêm tăng dần thay vì ghi đè.
- `delete_chunks_by_source()`: xóa chunk theo tên file khi cần index lại 1 tài liệu cụ thể.

### Hỏi đáp

```text
Câu hỏi → ask_pg()
  → follow-up detection (nếu có → kết hợp topic trước + câu hỏi mới)
  → embedding search ChromaDB (source-priority + keyword boosting)
  → tạo prompt
  → Groq LLM
    ├── Thành công → trả lời
    └── Lỗi/rate-limit → Gemini (2.5-flash → 2.0-flash → 2.0-flash-lite)
        └── Tất cả lỗi → Extractive fallback
  → lưu lịch sử + nguồn tham khảo vào SQLite
```

### Wikipedia fallback

```text
Câu trả lời "không đủ thông tin"
  → crawl Wikipedia tiếng Việt (wiki_crawler.py)
  → làm sạch HTML (BeautifulSoup)
  → thêm ngữ cảnh mới → hỏi lại LLM
  → lưu chunks vào ChromaDB (lần sau không cần crawl lại)
```

---

## Cài đặt và chạy (local)

### 1. Cài thư viện

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Tạo file `.env`

```env
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile

GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash

RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL=no-reply@yourdomain.com
```

- `GEMINI_API_KEY` nên có để làm fallback cho Groq.
- `RESEND_API_KEY` và `RESEND_FROM_EMAIL` dùng cho chức năng quên mật khẩu.

### 3. Chuẩn bị dữ liệu

Đặt file PDF lịch sử vào `data/pdf/`, sau đó chạy index:

```bash
python data_processing/run_pipeline.py
```

Pipeline sẽ tự động bỏ qua các file đã được index trước đó.

### 4. Chạy giao diện Streamlit

```bash
streamlit run frontend/app.py --server.port 8502
```

Mở trình duyệt tại `http://localhost:8502`.

### 5. Chạy API (tùy chọn)

```bash
python backend/api.py
```

API docs tại `http://localhost:8000/docs`.

---

## Triển khai trên Hugging Face Space

Project đã được triển khai tại: [https://huggingface.co/spaces/NguyenQuocVy2004/chatbot-lichsu](https://huggingface.co/spaces/NguyenQuocVy2004/chatbot-lichsu)

Cấu hình triển khai:

- **SDK**: Docker (`python:3.11-slim`, non-root user)
- **Entrypoint**: `scripts/start_space.py` → bootstrap dataset → chạy Streamlit trên port 7860
- **Dataset runtime**: tải từ HF Dataset repo qua `scripts/bootstrap_space_data.py`

### Biến môi trường trên Space

| Biến | Bắt buộc | Mô tả |
|---|---|---|
| `GROQ_API_KEY` | Có | API key Groq |
| `GROQ_MODEL` | Không | Model Groq (mặc định `llama-3.3-70b-versatile`) |
| `GEMINI_API_KEY` | Có | API key Gemini (fallback) |
| `GEMINI_MODEL` | Không | Model Gemini (mặc định `gemini-2.5-flash`) |
| `RESEND_API_KEY` | Có (nếu dùng quên mật khẩu) | API key gửi email qua Resend |
| `RESEND_FROM_EMAIL` | Có (nếu dùng quên mật khẩu) | Email người gửi (đã verify domain trong Resend) |
| `HF_DATASET_REPO` | Khuyên dùng | Repo chứa dataset runtime và chatbot.db |
| `HF_TOKEN` | Khuyên dùng | Token để đọc/ghi dataset repo private |
| `HF_DATASET_REVISION` | Không | Nhánh dataset (mặc định `main`) |
| `HF_DATASET_FORCE_SYNC` | Không | Đặt `1` để ép tải lại dataset khi khởi động |
| `APP_DATA_DIR` | Không | Thư mục dữ liệu runtime (mặc định `/tmp/app_data`) |
| `ADMIN_EMAILS` | Không | Danh sách email admin (phân cách bằng dấu phẩy) |

### Đồng bộ dữ liệu bền vững trên HF

- Khi Space khởi động: `scripts/bootstrap_space_data.py` tải `chatbot.db`, `csdl_vector/`, `pdf/` từ dataset repo. Bỏ qua nếu local manifest đã khớp remote (trừ khi `HF_DATASET_FORCE_SYNC=1`).
- Khi có thao tác ghi dữ liệu: `backend/db_sync.py` tự đồng bộ ngược lên dataset repo:
  - `chatbot.db` — rate-limited 30 giây.
  - File PDF — upload/xóa theo thao tác admin.
  - `csdl_vector/` — sau khi reindex hoặc thêm tài liệu.
  - `manifest.json` — cập nhật metadata mỗi lần sync.

---

## Công nghệ sử dụng

| Công nghệ | Vai trò |
|---|---|
| Python 3.11 | Ngôn ngữ chính |
| Streamlit | Giao diện người dùng |
| FastAPI + Uvicorn | API backend |
| ChromaDB | Vector database |
| SQLite | Lưu dữ liệu quan hệ |
| Sentence Transformers | Embedding E5 (`intfloat/multilingual-e5-base`) |
| Groq API | LLM chính (Llama 3.3 70B) |
| Google Gemini API | LLM dự phòng (chuỗi 3 model) |
| LangChain Text Splitters | Chunking văn bản |
| pypdf | Đọc PDF |
| BeautifulSoup + requests | Crawl / làm sạch Wikipedia |
| Resend API | Gửi email OTP |
| Docker | Triển khai trên HF Space |
| Hugging Face Hub | Đồng bộ dataset runtime |

---

## Tác giả

**Nguyễn Quốc Vỹ**
**MSSV: 226148**

Đồ án 2 — Chatbot Tra cứu Lịch sử Việt Nam.
